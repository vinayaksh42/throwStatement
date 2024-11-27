from flask import Flask, render_template, request, redirect, url_for
import os
import subprocess
import tempfile
import shutil
import re
import urllib.parse  # For URL encoding

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    error = request.args.get('error')
    return render_template('index.html', error=error)

@app.route('/compare', methods=['GET'])
def compare():
    repo_url = request.args.get('repo_url', '').strip()
    old_commit = request.args.get('old_commit', '').strip()
    new_commit = request.args.get('new_commit', '').strip()

    # Simple input validation
    if not repo_url or not old_commit or not new_commit:
        error = "All fields are required."
        return redirect(url_for('index', error=error))

    try:
        new_throws = get_new_throw_statements(repo_url, old_commit, new_commit)
        return render_template('result.html', new_throws=new_throws, repo_url=repo_url, old_commit=old_commit, new_commit=new_commit)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return redirect(url_for('index', error=error_message))

def get_new_throw_statements(repo_url, old_commit, new_commit):
    """
    Uses git diff to find new 'throw' statements added between two commits.
    Returns a list of tuples: (file_path, throw_statement_with_context).
    """
    temp_dir = tempfile.mkdtemp()
    repo_dir = os.path.join(temp_dir, "repo")

    try:
        # Clone the repository (shallow clone for efficiency)
        subprocess.run(
            ["git", "clone", "--depth", "1", "--no-checkout", repo_url, repo_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=120
        )

        # Fetch the specific commits
        subprocess.run(
            ["git", "fetch", "--depth", "1", "origin", old_commit, new_commit],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=60
        )

        # Use git diff to find new throw statements
        diff_output = subprocess.run(
            ["git", "diff", f"{old_commit}", f"{new_commit}", "--unified=0", "--", "*.java"],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=60
        ).stdout

        # Parse the diff output to find added 'throw' statements
        diff_lines = diff_output.splitlines()

        new_throw_statements = []
        pattern = re.compile(r'^\+\s*(.*\bthrow\b.*)$')  # Matches added lines containing 'throw'

        current_file = None
        hunk_started = False
        line_index = 0

        while line_index < len(diff_lines):
            line = diff_lines[line_index]

            # Detect file changes
            if line.startswith('diff --git'):
                # Extract the new file path
                match = re.match(r'^diff --git a/.* b/(.*)', line)
                if match:
                    current_file = match.group(1)
                else:
                    current_file = None
                line_index += 1
                continue

            # Skip index and file mode lines
            if (line.startswith('index ') or line.startswith('new file mode') or
                line.startswith('deleted file mode') or line.startswith('similarity index') or
                line.startswith('rename from') or line.startswith('rename to')):
                line_index += 1
                continue

            # Detect hunk headers
            if line.startswith('@@'):
                hunk_started = True
                line_index += 1
                continue

            if hunk_started:
                # Check for added lines with 'throw'
                if line.startswith('+'):
                    match = pattern.match(line)
                    if match:
                        # Found a new throw statement
                        throw_line = match.group(1).strip()
                        # Collect next 3 lines for context, if available
                        context_block = [throw_line]
                        context_line_index = line_index + 1
                        context_lines_collected = 0
                        while context_lines_collected < 3 and context_line_index < len(diff_lines):
                            next_line = diff_lines[context_line_index]
                            if next_line.startswith('+') or next_line.startswith(' '):
                                # Added or context line
                                context_block.append(next_line.lstrip('+ ').strip())
                                context_lines_collected += 1
                            elif next_line.startswith('-'):
                                # Removed line, skip
                                pass
                            else:
                                # End of hunk or diff metadata
                                break
                            context_line_index += 1
                        new_throw_statements.append((current_file, '\n'.join(context_block)))
                line_index += 1
            else:
                line_index += 1

        return new_throw_statements

    except subprocess.TimeoutExpired:
        raise Exception("Operation timed out. Please try again later.")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error running git commands: {e.stderr}")
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)

if __name__ == '__main__':
    app.run(debug=True)
