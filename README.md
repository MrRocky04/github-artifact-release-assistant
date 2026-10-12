# GitHub Artifact Release Assistant

A local web application for preparing Android `.aar` artifact uploads and SDK releases. It provides a React interface backed by a Python server and uses Git and the GitHub CLI (`gh`) for repository operations.

**This project is intended to run on your computer. It is not a GitHub Pages website.** GitHub Pages only serves static files and cannot run this application's Python backend or GitHub CLI commands. The repository contains the source code; it does not automatically publish a website.

## Requirements

- Python 3.10 or later
- Node.js and npm
- Git
- GitHub CLI (`gh`)
- A GitHub account authenticated in the GitHub CLI

Install GitHub CLI if needed, then sign in once:

```powershell
gh auth login
```

## Build and run on Windows

Open PowerShell in the project root (`release_assistant-web`). Build the frontend once:

```powershell
cd frontend
npm install
npm run build
cd ..
```

Start the application:

```powershell
python main.py
```

The application opens in your browser at `http://127.0.0.1:8765`. Keep the terminal open while using it. Press `Ctrl+C` in that terminal to stop the server.

To build the frontend and start the application in one command, run this from the project root:

```powershell
cd frontend
npm start
```

## How it works

1. Upload an Android `.aar` file. The app checks that the file is a ZIP-based AAR archive.
2. Enter artifact information and, when creating a release, answer the release and testing questions.
3. Select a new or existing release branch and review the proposed repository changes.
4. Confirm the operation. The app uses Git and the GitHub CLI to push the artifact and, for the release workflow, create a GitHub release/tag and pull request.

The **Upload Artifact** option uploads the AAR to the selected branch without creating a release/tag or pull request. The **Release / Questionnaire Information** option records release information in the repository `README.md`, creates the GitHub release/tag, and opens a pull request.

## Manage questions

Use **Manage Questions** in the sidebar to add or remove questionnaire items. Custom questions are saved locally in `questions_config.json`. This file is generated on first run and is ignored by Git so that personal question changes are not accidentally committed.

## Project structure

```text
main.py                    Starts the local application and opens the browser
server.py                  Python HTTP server and JSON API
workflow.py                Release workflow and review/confirmation steps
github_cli.py               Git and GitHub CLI helpers
questions.py                Default questions and local question management
report_generator.py         README and pull request content generation
parser.py                   Original local-search helper
config.py                   Local paths and server settings
requirements.txt            Python dependency note
frontend/
  src/                     Readable React components and CSS source
  build.mjs                Builds the frontend into frontend/dist/
  start.mjs                Starts the Python server after the frontend build
  package.json              Frontend scripts and dependencies
```

`frontend/dist/` and `frontend/node_modules/` are generated locally and are not committed. Run the build commands above before starting the app from a fresh clone.

## Notes

- The Python backend uses the standard library; no third-party Python packages are required.
- Git and the GitHub CLI must be installed and available in `PATH`.
- The app runs on `127.0.0.1` by default, so it is intended for local use.
- GitHub Pages deployment configuration is intentionally not included. Pushing this repository to GitHub only stores the source code; it does not host the application.
