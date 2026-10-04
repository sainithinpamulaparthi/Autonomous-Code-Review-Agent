# 🤖 Autonomous Code Review Agent

An **AI-assisted Autonomous Code Review Agent** that automatically analyzes source code, detects bugs, security vulnerabilities, and code-quality issues, explains the problems in simple language, prioritizes them based on severity, and provides suggested fixes.

The system combines **static code analysis, GitHub integration, SonarQube, and Large Language Models (LLMs)** to provide an automated and intelligent code-review workflow.

---

## 📌 Project Overview

Code review is an important part of software development, but manually reviewing large projects can be time-consuming and difficult.

The **Autonomous Code Review Agent** automates this process by analyzing source code and identifying potential problems before they reach production.

The system can:

- 🔍 Detect bugs and coding issues
- 🔐 Identify common security vulnerabilities
- 📊 Prioritize issues based on severity
- 🧠 Use an LLM to explain detected problems
- 💡 Suggest possible fixes
- 🐙 Analyze GitHub repositories
- 🔄 Review GitHub Pull Requests
- 📄 Generate detailed code-review reports
- 🛡️ Perform secret and credential scanning
- ⚡ Run static analysis locally without requiring an LLM
- 🐳 Support Docker and SonarQube
- 🌐 Provide a Flask-based web interface
- 💻 Provide CLI and REST API support

---

## 🎯 Objectives

The main objectives of the project are:

1. Automate the software code-review process.
2. Detect bugs, security vulnerabilities, and code-quality problems.
3. Provide understandable explanations for detected issues.
4. Prioritize issues according to their severity and impact.
5. Generate useful fix recommendations.
6. Reduce the manual effort required during code review.

---

## ✨ Key Features

### 🔍 Automated Static Code Analysis

The built-in analyzer checks source code using Python AST analysis and rule-based analysis.

It can identify:

- Syntax errors
- SQL injection patterns
- Shell injection
- `eval()` / `exec()` usage
- Hard-coded secrets
- AWS keys
- Unsafe `pickle` usage
- Unsafe YAML loading
- Weak hashing algorithms
- Disabled TLS verification
- Debug mode
- Mutable default arguments
- Bare exception handling
- Silently swallowed exceptions
- High cyclomatic complexity
- Very large functions
- Unused imports
- `range(len())` patterns
- String concatenation inside loops
- TODO/FIXME comments
- JavaScript `eval()`
- Potential `innerHTML` XSS issues

---

## 🔐 Security Analysis

The system performs security-oriented checks for common vulnerabilities such as:

- SQL Injection
- Command/Shell Injection
- Cross-Site Scripting (XSS)
- Hard-coded credentials
- API keys and secrets
- AWS access keys
- Unsafe deserialization
- Weak cryptographic hashing
- Disabled SSL/TLS verification
- Dangerous dynamic code execution

The goal is to identify security risks early in the development lifecycle.

---

## 🧠 AI-Powered Code Explanation

The system can optionally use a Large Language Model to improve the explanation of detected issues.

The LLM can:

- Understand the surrounding code context
- Explain why the issue is dangerous
- Provide human-readable explanations
- Suggest possible improvements
- Generate more meaningful fix recommendations

The project supports local LLM execution through **Ollama**, allowing the system to work without an external API key.

---

## 🏗️ System Architecture

The project follows a modular architecture:

~~~text
                    ┌──────────────────────┐
                    │      Developer       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Flask Web UI     │
                    │      / REST API      │
                    └──────────┬───────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │   Autonomous Reviewer     │
                 │      Orchestration        │
                 └─────────────┬─────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
      ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
      │   GitHub     │ │    Static    │ │  SonarQube   │
      │ Integration  │ │   Analyzer   │ │   Analysis   │
      └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
             │                 │                │
             └─────────────────┼────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │ Issue Aggregation &  │
                    │    De-duplication    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Severity & Risk      │
                    │     Prioritization   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     LLM / Ollama     │
                    │ Explanation & Fixes  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Review Report      │
                    │  Score + Findings    │
                    └──────────────────────┘
~~~

---

## 🔄 Workflow

The overall workflow of the Autonomous Code Review Agent is:

~~~text
1. Source Code Input
          ↓
2. GitHub Repository / Uploaded File / Pasted Code
          ↓
3. Source Code Collection
          ↓
4. Static Code Analysis
          ↓
5. SonarQube Analysis (Optional)
          ↓
6. Issue Aggregation
          ↓
7. Duplicate Issue Removal
          ↓
8. Severity Classification
          ↓
9. Risk Prioritization
          ↓
10. LLM Explanation & Fix Recommendation
          ↓
11. Code Review Score
          ↓
12. Final Review Report
~~~

---

## 📊 Issue Severity

Detected issues are categorized according to their severity:

| Severity | Description |
|----------|-------------|
| 🔴 CRITICAL | Very serious security or code issue |
| 🟠 MAJOR | Important issue requiring attention |
| 🟡 MINOR | Lower-impact quality or maintainability issue |
| 🔵 INFO | Informational recommendation |

The system calculates an overall **Code Review Score from 0–100** based on detected issues.

---

## 🧩 Main Components

### 1. Static Analyzer

The built-in static analyzer performs local code analysis using:

- Python AST
- Regular expressions
- Custom security rules
- Code-quality rules
- JavaScript/TypeScript checks
- Secret scanning

This component works offline and does not require an LLM.

### 2. SonarQube Integration

SonarQube can provide additional static-analysis results.

The agent retrieves SonarQube issues and combines them with the built-in analyzer results.

The system also performs issue de-duplication to avoid displaying the same problem multiple times.

### 3. GitHub Integration

The GitHub integration allows the system to:

- Analyze public repositories
- Analyze private repositories with a GitHub token
- Retrieve repository source files
- Analyze Pull Requests
- Parse changed files
- Generate Pull Request review information

### 4. LLM Integration

The LLM component improves explanations and fix recommendations.

The project can use:

- Ollama
- OpenAI-compatible models

Ollama is especially useful for local development because it does not require an external API key.

### 5. Review Engine

The review engine coordinates the complete process:

- Collecting source code
- Running analyzers
- Combining findings
- Removing duplicates
- Prioritizing issues
- Generating explanations
- Calculating the review score
- Producing the final report

---

## 🛠️ Technologies Used

| Technology | Purpose |
|------------|---------|
| Python | Core programming language |
| Flask | Web application and REST API |
| GitHub API | Repository and Pull Request integration |
| SonarQube | Static code quality and security analysis |
| LangChain | LLM integration |
| Ollama | Local LLM execution |
| Docker | Containerization |
| HTML/CSS | Web interface |
| Python AST | Python source-code analysis |
| Git | Version control |

---

## 💻 System Requirements

### Hardware

Recommended minimum configuration:

- Processor: Intel Core i5 or equivalent
- RAM: 8 GB or higher
- Storage: At least 10 GB free space
- Operating System: Windows 10/11, Linux, or macOS

### Software

- Python 3.10+
- Git
- Docker Desktop
- Ollama (optional)
- SonarQube (optional)
- Modern web browser

---

# 🚀 Installation

## 1. Clone the Repository

~~~bash
git clone https://github.com/sainithinpamulaparthi/Autonomous-Code-Review-Agent.git
cd Autonomous-Code-Review-Agent
~~~

---

## 2. Create a Virtual Environment

### Windows

~~~powershell
python -m venv .venv
.venv\Scripts\activate
~~~

### Linux / macOS

~~~bash
python3 -m venv .venv
source .venv/bin/activate
~~~

---

## 3. Install Dependencies

~~~bash
pip install -r requirements.txt
~~~

---

## 4. Configure Environment Variables

Create a `.env` file in the project root.

Example:

~~~env
LLM_PROVIDER=ollama
LLM_MODEL=gemma2:2b
OLLAMA_BASE_URL=http://localhost:11434
~~~

The `.env` file should **not be uploaded to GitHub** because it may contain private credentials.

---

# 🧠 Ollama Setup

Ollama allows the project to use a local LLM without requiring an external API key.

Install Ollama and download a supported model.

Example:

~~~powershell
ollama pull gemma2:2b
~~~

Check installed models:

~~~powershell
ollama list
~~~

Start Ollama if required:

~~~powershell
ollama serve
~~~

Example configuration:

~~~env
LLM_PROVIDER=ollama
LLM_MODEL=gemma2:2b
OLLAMA_BASE_URL=http://localhost:11434
~~~

The application can continue to perform static analysis even if the LLM is unavailable.

---

# 🔐 GitHub Token

A GitHub token is optional for public repository analysis.

A token may be required for:

- Private repositories
- Higher GitHub API rate limits
- Pull Request operations
- Posting review comments

Example:

~~~env
GITHUB_TOKEN=your_github_token
~~~

Never commit your GitHub token to the repository.

---

# 📈 SonarQube Setup

SonarQube can be used as an optional additional analysis engine.

Start SonarQube using Docker:

~~~powershell
docker run -d --name sonarqube -p 9000:9000 sonarqube:lts-community
~~~

Open:

~~~text
http://localhost:9000
~~~

The SonarQube service provides additional information about:

- Bugs
- Vulnerabilities
- Code smells
- Security issues
- Code quality

Example configuration:

~~~env
SONAR_HOST_URL=http://localhost:9000
SONAR_TOKEN=your_sonar_token
SONAR_PROJECT_KEY=your_project_key
~~~

The agent reads the available SonarQube analysis results and combines them with its built-in analysis.

---

# ▶️ Running the Application

After installing dependencies and activating the virtual environment:

~~~powershell
python app.py
~~~

Open the application in your browser:

~~~text
http://localhost:5000
~~~

---

# 🌐 Web Interface

The Flask web interface allows users to submit source code and perform code reviews.

Typical workflow:

~~~text
Open Web Application
        ↓
Select Analysis Method
        ↓
Paste Code / Upload File / Enter GitHub Repository
        ↓
Start Code Review
        ↓
Static Analysis
        ↓
Optional SonarQube Analysis
        ↓
Optional LLM Explanation
        ↓
View Review Dashboard
~~~

The dashboard displays:

- Overall review score
- Number of detected issues
- Severity levels
- Issue descriptions
- Affected code
- Suggested fixes
- Security findings
- Quality findings

---

# 🧪 Demo Mode

The project includes a Demo Mode for demonstrating the system without external services.

Demo Mode can work without:

- GitHub token
- SonarQube
- LLM API
- External services

This makes it suitable for:

- College demonstrations
- Project presentations
- Testing
- Offline development

---

# 🧪 Testing

Run the project tests using:

~~~powershell
python -m unittest discover -s tests -t .
~~~

The project includes automated tests for important components of the code-review system.

---

# 💻 Command Line Usage

The project also provides command-line functionality through `cli.py`.

Example:

~~~powershell
python cli.py
~~~

The CLI can be used for automation and CI/CD workflows.

---

# 🔌 REST API

The Flask application provides REST API functionality for integrating the code-review agent with other applications.

The API can be used to:

- Submit source code
- Start code analysis
- Retrieve review results
- Check application health

A health endpoint is also available for checking application status.

---

# 🔄 Pull Request Review

The project can support automated Pull Request reviews using GitHub integration.

The workflow is:

~~~text
Developer Creates Pull Request
             ↓
       GitHub Webhook
             ↓
     Autonomous Code Review
             ↓
       Source Retrieval
             ↓
      Static Analysis
             ↓
    Optional SonarQube
             ↓
    Issue Prioritization
             ↓
     LLM Explanation
             ↓
      Review Report
             ↓
   Pull Request Feedback
~~~

The system can focus on issues introduced by the Pull Request instead of analyzing unrelated existing code.

---

# 🐳 Docker Support

Docker can be used to simplify deployment and environment management.

The project can be containerized so that the application and its dependencies can run consistently across different environments.

Example:

~~~bash
docker compose --profile full up --build
~~~

---

# 📁 Project Structure

~~~text
Autonomous-Code-Review-Agent/
│
├── app.py
├── cli.py
├── requirements.txt
├── .env.example
├── README.md
│
├── agent/
│   ├── static_analyzer/
│   ├── rules.py
│   ├── sonar_client/
│   ├── llm.py
│   ├── github_client/
│   ├── reviewer/
│   └── demo.py
│
├── templates/
│   └── Web UI templates
│
├── static/
│   └── CSS / JavaScript / static assets
│
├── sample_code/
│   └── Demo source-code examples
│
└── tests/
    └── test_agent.py
~~~

---

# 🔎 Example Detection Categories

## Security

- SQL Injection
- Shell Injection
- Hard-coded Secrets
- AWS Credentials
- Unsafe `eval()` / `exec()`
- Unsafe Pickle
- Unsafe YAML Loading
- Weak MD5/SHA-1 Hashing
- Disabled TLS Verification
- JavaScript XSS
- Debug Configuration

## Bugs

- Syntax Errors
- Mutable Default Arguments
- Bare `except`
- Silently Ignored Exceptions

## Code Quality

- High Cyclomatic Complexity
- Large Functions
- Unused Imports
- `range(len())`
- String Concatenation in Loops
- TODO/FIXME Comments

---

# 🏆 Advantages

- ✅ Automates repetitive code-review tasks
- ✅ Detects security vulnerabilities early
- ✅ Reduces manual review effort
- ✅ Provides understandable explanations
- ✅ Provides suggested fixes
- ✅ Supports GitHub repositories
- ✅ Supports Pull Request analysis
- ✅ Works with local LLMs
- ✅ Can operate without an LLM
- ✅ Can integrate with SonarQube
- ✅ Provides severity-based prioritization
- ✅ Suitable for CI/CD integration
- ✅ Modular and extensible architecture

---

# 🆚 Traditional Code Review vs Proposed System

| Feature | Traditional Manual Review | Autonomous Code Review Agent |
|---------|----------------------------|-------------------------------|
| Manual effort | High | Reduced |
| Automated analysis | Limited | Yes |
| Security detection | Depends on reviewer | Automated rules |
| Issue prioritization | Manual | Automated |
| AI explanations | No | Optional |
| Fix suggestions | Manual | Automated |
| GitHub integration | Manual | Supported |
| Pull Request analysis | Manual | Supported |
| SonarQube integration | Separate | Integrated |
| Local LLM support | No | Yes |
| Review score | Manual | Automated |

---

# 💡 Why This Project Is Different

Many existing AI coding tools focus mainly on generating or fixing code.

This project focuses specifically on the **code-review lifecycle**.

Instead of directly modifying code without analysis, the system:

1. Collects the source code.
2. Performs static analysis.
3. Detects possible problems.
4. Combines multiple analysis sources.
5. Removes duplicate findings.
6. Prioritizes issues by severity.
7. Uses an LLM to explain important findings.
8. Provides suggested fixes.
9. Generates a structured review report.

This makes the system useful as an **automated code-review assistant** rather than only a code-generation or code-optimization tool.

---

# 🔒 Reliability and Fallback Mechanism

The project is designed so that external services are optional.

### If GitHub is unavailable

Local code or uploaded files can still be analyzed.

### If SonarQube is unavailable

The built-in static analyzer continues to perform the review.

### If the LLM is unavailable

The system can fall back to the built-in rule explanations and suggested fixes.

### If an LLM request fails

The review process should not be blocked by the LLM.

This architecture makes the system more reliable for demonstrations and practical usage.

---

# ⚠️ Limitations

Although the project provides automated code analysis, it has some limitations:

- Deep analysis is currently strongest for Python.
- JavaScript/TypeScript analysis uses a smaller set of rules.
- Other programming languages may primarily receive basic scanning.
- Rule-based analysis can produce false positives or false negatives.
- The current system does not perform complete taint analysis.
- LLM-generated recommendations should be reviewed by a developer.
- GitHub API limitations may restrict large repositories.
- Pull Request analysis may be limited by file and file-size limits.
- Review reports may be stored temporarily depending on configuration.

---

# 🔮 Future Scope

1. Support more programming languages such as Java, C++, Go, and JavaScript.
2. Add advanced AI-based vulnerability and bug detection.
3. Improve automated code-fix generation.
4. Integrate directly with CI/CD pipelines and GitHub Actions.
5. Add automated Pull Request review comments.
6. Introduce historical code-quality tracking and analytics.

---

# 📚 Applications

The Autonomous Code Review Agent can be useful for:

- Software development teams
- Educational institutions
- Student software projects
- Open-source projects
- GitHub repositories
- CI/CD pipelines
- Security-focused development
- Automated Pull Request analysis

---

# 🎓 Academic Relevance

This project demonstrates the practical application of:

- Artificial Intelligence
- Machine Learning / Large Language Models
- Natural Language Processing
- Static Code Analysis
- Software Engineering
- Cybersecurity
- GitHub API Integration
- Cloud/Container Technologies
- Web Application Development

It combines these technologies into a single automated software-engineering solution.

---

# 📊 Expected Output

After completing a review, the system provides information such as:

~~~text
Code Review Score: 82/100

CRITICAL: 1
MAJOR: 3
MINOR: 5
INFO: 2

Security Issues
    ├── Hard-coded secret
    └── Unsafe command execution

Code Quality Issues
    ├── High complexity
    └── Unused import

Recommendations
    ├── Remove sensitive credentials
    ├── Validate user input
    └── Refactor complex functions
~~~

---

# 🧑‍💻 Development Team

**Project:** Autonomous Code Review Agent

**Domain:** Artificial Intelligence / Software Engineering / Cybersecurity

**Primary Language:** Python

**Framework:** Flask

**AI Technology:** Large Language Models

**Static Analysis:** Python AST / Custom Rules / SonarQube

**Containerization:** Docker

---

# 📜 License

This project is developed for educational and academic purposes.

---

# ⭐ Acknowledgement

This project was developed as an academic project to explore the application of Artificial Intelligence and Large Language Models in automated software code review.

---

# 🚀 Conclusion

The **Autonomous Code Review Agent** provides an automated approach to software code review by combining static analysis, security scanning, GitHub integration, SonarQube, and Large Language Models.

The system helps developers identify potential problems earlier, understand why an issue occurs, prioritize important findings, and receive useful suggestions for improving their code.

The modular architecture also provides a foundation for future enhancements such as additional programming-language support, advanced AI-based analysis, automated code fixing, CI/CD integration, and fully automated Pull Request reviews.

---

⭐ **If you find this project useful, consider giving the repository a star!**
