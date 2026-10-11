# GitHub Artifact Release Assistant (web UI)

Upload an Android `.aar` artifact, answer release / testing questions, and let the
tool create the branch, update `README.md`, push, create the GitHub release/tag and
open a Pull Request — now from a website that runs on your own computer.

All GitHub operations still go through **Git** and the **GitHub CLI (`gh`)**.
The Python standard library is the only Python dependency.

## Requirements
- Python 3.10+
- Git and GitHub CLI (`gh`) — run `gh auth login` once beforehand
- Node.js + npm **only if** you want to rebuild the website (a built copy is included in `frontend/dist`)

## Run
```bash
python main.py
```
This starts the backend and opens http://127.0.0.1:8765 in your browser.

Optional (rebuild the React frontend, then start):
```bash
cd frontend
npm install
npm start          # builds the UI and starts main.py
```

## Flow
1. **Start a release** → upload the artifact (only `.aar`, validated as a ZIP archive)
2. **Artifact information** questions
3. Choose **Upload Artifact** (branch only) or **Release / Questionnaire Information**
4. Release information → purpose (Internal Testing / Personal Testing / Production) and its questions
5. Verify answers → choose a new or existing branch → review the staged changes
6. Confirm → commit, push, release/tag (AAR attached) and Pull Request

## Manage Questions
Sidebar → **Manage Questions**. Add a question to one of: Artifact information,
Release information, Internal testing, Personal testing or Production, and choose
whether it is required and whether it is a Yes/No or text answer. Deleting asks for
confirmation. Questions are stored in `questions_config.json` (created on first run;
delete the file to restore the defaults). Answers to added questions are written to the
matching README section. Version, repository and source branch cannot be removed
because the branch/release/PR steps need them.

## Project structure
```
main.py               start here (starts the server, opens the browser)
server.py             local HTTP server + JSON API (standard library)
workflow.py           the release workflow (the former CLI logic in main.py)
questions.py          default questions + add/remove store
github_cli.py         git / gh helpers
report_generator.py   README + Pull Request text
parser.py             original local-search helper (no longer used by the UI)
config.py             paths, port, defaults
frontend/             React source (src/) and built site (dist/)
```

## Architecture

The application uses a React frontend with a Python backend. The backend manages the release workflow and executes Git and GitHub CLI commands to perform repository operations.

                    +----------------------+
                    |    User / Browser    |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |     React Web UI     |
                    |     (Frontend)       |
                    +----------+-----------+
                               |
                               | HTTP / JSON API
                               v
                    +----------------------+
                    |  Python HTTP Server  |
                    |      server.py       |
                    +----------+-----------+
                               |
                +--------------+--------------+
                |              |              |
                v              v              v
    +------------------+ +----------------+ +------------------+
    | Question         | | Release        | | AAR Upload       |
    | Management       | | Workflow       | | Handler          |
    | questions.py     | | workflow.py    | | server.py        |
    +--------+---------+ +--------+-------+ +--------+---------+
             |                    |                  |
             v                    |                  v
    +------------------+          |         +------------------+
    | questions_config |          |         | Local AAR Uploads |
    | .json            |          |         | .artifact-        |
    +------------------+          |         | assistant/uploads |
                                  |
                    +-------------+-------------+
                    |             |             |
                    v             v             v
           +----------------+ +-------------+ +------------------+
           | Report         | | GitHub CLI  | | Local Repository |
           | Generator      | | Helpers     | | Workspace        |
           | report_        | | github_     | | .artifact-       |
           | generator.py   | | cli.py      | | assistant/       |
           +-------+--------+ +------+------+ | repositories/    |
                   |                 |        +------------------+
                   v                 v
           +----------------+ +------------------+
           | README / PR    | | Git + GitHub CLI  |
           | Content        | | (gh)              |
           +----------------+ +--------+---------+
                                       |
                                       v
                              +--------------------+
                              | Target GitHub      |
                              | Repository         |
                              +--------------------+

### Main Components

- **React Frontend:** Provides the artifact upload interface, release questionnaire, change review, and question management.
- **Python HTTP Server:** Serves the built frontend and handles API requests from the browser.
- **Release Workflow:** Validates questionnaire answers, prepares branch changes, and coordinates the selected operation.
- **Question Management:** Stores the default and user-added questions in `questions_config.json`.
- **Report Generator:** Creates release documentation for `README.md` and the pull request description.
- **Git and GitHub CLI Helpers:** Handle repository cloning, branch operations, commits, pushes, GitHub releases, and pull requests.
- **Local Workspace:** Stores uploaded AAR files and the working repository clones on the user's computer.

## Operation Behaviour

| Operation | Result |
|---|---|
| **Upload Artifact** | Commits and pushes the AAR to the selected branch. It does not create a GitHub release/tag or pull request. |
| **Release / Questionnaire Information** | Records the AAR and release information, pushes the changes, creates a GitHub release/tag with the AAR attached when applicable, and opens a pull request. |

