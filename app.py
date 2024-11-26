from flask import Flask, render_template, request
import os
import subprocess
import tempfile
import shutil
import re

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        repo_url = request.form['repo_url'].strip()
        old_commit = request.form['old_commit'].strip()
        new_commit = request.form['new_commit'].strip()

        # Validation
        if not repo_url or not old_commit or not new_commit:
            error = "All fields are required."
            return render_template('index.html', error=error)

        try:
            new_throws = get_new_throw_statements(repo_url, old_commit, new_commit)
            return render_template('result.html', new_throws=new_throws)
        except Exception as e:
            error = f"An error occurred: {str(e)}"
            return render_template('index.html', error=error)
    else:
        return render_template('index.html')

def get_new_throw_statements(repo_url, old_commit, new_commit):
    """
    Uses git diff to find new 'throw' statements added between two commits.
    Returns a list of tuples: (file_path, throw_statement_with_context).
    """
    temp_dir = tempfile.mkdtemp()
    repo_dir = os.path.join(temp_dir, "repo")

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--no-checkout", repo_url, repo_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=120
        )

        # Fetch commits for different versions
        subprocess.run(
            ["git", "fetch", "--depth", "1", "origin", old_commit, new_commit],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=60
        )

        diff_output = subprocess.run(
            ["git", "diff", f"{old_commit}", f"{new_commit}", "--unified=0", "--", "*.java"],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=60
        ).stdout

        diff_lines = diff_output.splitlines()

        new_throw_statements = []
        pattern = re.compile(r'^\+\s*(.*\bthrow\b.*)$')

        current_file = None
        hunk_started = False
        line_index = 0

        while line_index < len(diff_lines):
            line = diff_lines[line_index]

            if line.startswith('diff --git'):
                match = re.match(r'^diff --git a/.* b/(.*)', line)
                if match:
                    current_file = match.group(1)
                else:
                    current_file = None
                line_index += 1
                continue

            if (line.startswith('index ') or line.startswith('new file mode') or
                line.startswith('deleted file mode') or line.startswith('similarity index') or
                line.startswith('rename from') or line.startswith('rename to')):
                line_index += 1
                continue

            if line.startswith('@@'):
                hunk_started = True
                line_index += 1
                continue

            if hunk_started:
                if line.startswith('+'):
                    match = pattern.match(line)
                    if match:
                        throw_line = match.group(1).strip()
                        context_block = [throw_line]
                        context_line_index = line_index + 1
                        context_lines_collected = 0
                        while context_lines_collected < 3 and context_line_index < len(diff_lines):
                            next_line = diff_lines[context_line_index]
                            if next_line.startswith('+') or next_line.startswith(' '):
                                context_block.append(next_line.lstrip('+ ').strip())
                                context_lines_collected += 1
                            elif next_line.startswith('-'):
                                pass
                            else:
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
        shutil.rmtree(temp_dir)

if __name__ == '__main__':
    app.run()