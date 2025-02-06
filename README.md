# Agile Project Management Dashboard

## 📋 Overview
The **Agile Project Management Dashboard** is a web-based application developed during the **Infosys Springboard Internship**. The dashboard aims to simplify and streamline project management processes, offering project tracking, task management, and data visualization in an easy-to-use interface. The project uses modern web technologies, including Flask, SQLite, HTML, CSS, JavaScript, SQLAlchemy, Flask-Login, Pandas, and Plotly for creating an interactive and user-friendly environment for managing agile projects.

## 🛠️ Features
- **User Authentication**: Secure login and registration using Flask-Login.
- **Project and Task Management**: Create, update, and delete tasks while tracking their progress.
- **Data Visualization**: Interactive visualizations for project status and task completion using Plotly charts.
- **PDF Export**: Export project reports, including task data and project statistics, to PDF.
- **Team Collaboration**: Efficiently assign tasks and manage project teams.
- **User-Friendly Interface**: Clean and intuitive frontend built with HTML, CSS, and JavaScript.
- **Responsive Design**: Mobile-friendly UI for easy access on all devices.

## 🚀 Tech Stack
- **Backend**: Flask, SQLAlchemy, SQLite
- **Frontend**: HTML5, CSS3, JavaScript
- **Authentication**: Flask-Login
- **Data Handling**: Pandas for processing data
- **Data Visualization**: Plotly for interactive charts and graphs
- **PDF Export**: Custom logic to export data to PDF
- **Version Control**: Git for version management

## 🛠️ Installation and Setup

### Prerequisites
Ensure the following are installed:
- Python 3.10
- pip (Python package installer)

### Clone the Repository
```bash
git clone <repository_url>
cd <project_folder>
```
Install Dependencies
Navigate to the project folder and install the required dependencies using the following command:

```bash

pip install -r requirements.txt
```
Set Up the Database
Initialize the SQLite database by running the following command:


```bash

python main.py
```
Visit the application in your browser at http://localhost:5000.

## 🎮 Usage
### User Authentication
- Login: Use the login form to authenticate users and access the dashboard.
- Registration: New users can register via the registration page.
### Dashboard
- View the project’s progress, task completion rates, and project statistics.
- Task information such as deadlines, completion status, and team member assignments are displayed.
### Task Management
- Product Owner can add, modify, or delete tasks from the project.
- He can also assign tasks to team members and track their progress.
### Data Visualization
- Interactive charts (task completion, project progress) powered by Plotly.
- Visual representation of key metrics to help track project success.
### PDF Export
Export project data and progress to PDF using custom logic, making it easy to generate reports.
📝 Contributing
Contributions are welcome! To contribute to the project:

## 📝 Contributing
Contributions are welcome! To contribute to the project:
1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Ensure your code follows the project's style and is well-documented.
4. Submit a pull request.
