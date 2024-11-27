from flask import Flask, render_template, request, redirect, url_for
import urllib.parse  # For URL encoding
@app.route('/', methods=['GET'])
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
        # Clone the repository (shallow clone for efficiency)
        # Fetch the specific commits
        # Use git diff to find new throw statements
        # Parse the diff output to find added 'throw' statements
        pattern = re.compile(r'^\+\s*(.*\bthrow\b.*)$')  # Matches added lines containing 'throw'
            # Detect file changes
                # Extract the new file path
            # Skip index and file mode lines
            # Detect hunk headers
                # Check for added lines with 'throw'
                        # Found a new throw statement
                        # Collect next 3 lines for context, if available
                                # Added or context line
                                # Removed line, skip
                                # End of hunk or diff metadata
        # Clean up temporary directory
    app.run(debug=True)