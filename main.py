from flask import Flask, redirect, url_for, render_template, flash, jsonify, request
from routers.team1 import login_bp, login_manager # Import the auth blueprint
from database import db  # Import the db instance
import os
from models import (
    ProjectDetails,
    ProductOwner,
    UserStories,
    ScrumMasters,
    Users,
    ProjectUsers,
    SprintCalendar,
    Tasks,
)
import traceback
from datetime import datetime
import send_mail as sm
from flask_login import user_logged_in, user_logged_out
from datetime import date
from datetime import datetime, timedelta
import random
import io
import pandas as pd
import matplotlib.pyplot as plt
import base64
from flask import send_file
from fpdf import FPDF
from io import BytesIO
import schedule
import time
from threading import Thread

app = Flask(__name__)
login_manager.init_app(app)
login_manager.login_view = "auth.login"

# Configurations
app.config["SECRET_KEY"] = "8BYkEfBA6O6donzWlSihBXox7C0sKR6b"
app.config["SESSION_COOKIE_NAME"] = "your_session_cookie_name"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(app.instance_path, 'global.db')}"
)
os.makedirs(app.instance_path, exist_ok=True)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# app.config["SQLALCHEMY_ECHO"] = False
# Set the upload folder
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')




# Initialize extensions
db.init_app(app)

# Register the auth blueprint with the url_prefix 'auth'
app.register_blueprint(login_bp, url_prefix="/auth")



# Create tables if necessary
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return redirect('/auth')

# Dashboard Logic
@app.route("/projects/<role>/<int:userid>")
def projects(role,userid):
    projects_data = ProjectDetails.query.all()
    print(projects_data)
    total_projects = ProjectDetails.query.count()
    active_projects = ProjectDetails.query.filter_by(Status="active").count()
    on_hold_projects = ProjectDetails.query.filter_by(Status="on hold").count()
    user_name = Users.query.filter_by(UserID=userid).first().Name


    projects = [
        {
            "project_name": project.ProjectName,
            "product_owner": project.product_owner.Name,
            "start_date": project.StartDate,
            "end_date": project.EndDate,
            "revised_end_date": project.RevisedEndDate,
            "status": project.Status,
            "project_id": project.ProjectId,
        }
        for project in projects_data
    ]
    return render_template(
        "Dashboard.html",
        projects=projects,
        total_projects=total_projects,
        active_projects=active_projects,
        on_hold_projects=on_hold_projects,
        user_name=user_name,
        role=role
    )


@app.route("/api/product_owners", methods=["GET"])
def get_product_owners():
    owners = ProductOwner.query.all()
    return jsonify(
        [{"id": owner.ProductOwnerId, "name": owner.Name} for owner in owners]
    )


@app.route("/api/scrum_masters", methods=["GET"])
def scrumMasters():
    smasters = ScrumMasters.query.all()
    return jsonify(
        [{"id": smaster.ScrumMasterID, "name": smaster.Name} for smaster in smasters]
    )


@app.route("/api/users", methods=["GET"])
def users():
    users = Users.query.all()
    return jsonify([{"id": user.UserID, "name": user.UserName} for user in users])


@app.route("/addproject")
def addproject():
    return render_template("index.html")


def get_all_scrum_masters():
    scrum_masters = ScrumMasters.query.all()  # Assuming ScrumMaster is your model
    return [{"id": sm.ScrumMasterID, "name": sm.Name} for sm in scrum_masters]


@app.route("/editproject/<int:project_id>", methods=["GET", "POST"])
def edit_project(project_id):
    if request.method == "GET":
        try:
            # Fetch project details
            project = ProjectDetails.query.filter_by(ProjectId=project_id).first()
            scrum_masters = get_all_scrum_masters()
            print(scrum_masters)
            if not project:
                return jsonify({"error": "Project not found"}), 404

            # Prepare data for the form
            project_data = {
                "ProjectId": project.ProjectId,
                "ProductOwnerId": project.ProductOwnerId,
                "ProjectName": project.ProjectName,
                "ProjectDescription": project.ProjectDescription,
                "StartDate": project.StartDate,
                "EndDate": project.EndDate,
                "RevisedEndDate": project.RevisedEndDate,
                "Status":project.Status.lower(),
                "sprints": [
                    {
                        "SprintId": sprint.SprintId,
                        "SprintNo": sprint.SprintNo,
                        "ScrumMasterID": sprint.ScrumMasterID,
                        "StartDate": sprint.StartDate,
                        "EndDate": sprint.EndDate,
                        "Velocity": sprint.Velocity,
                        "user_stories": [
                            {
                                "PlannedSprint": story.PlannedSprint,
                                "ActualSprint": story.ActualSprint,
                                "Description": story.Description,
                                "StoryPoint": story.StoryPoint,
                                "MOSCOW": story.MOSCOW,
                                "Assignee": story.Assignee,
                                "Status": story.Status,
                            }
                            for story in sprint.user_stories
                        ],
                    }
                    for sprint in project.sprints
                ],
            }

            # Render form with pre-filled data
            return render_template(
                "edit_project.html",
                project=project_data,
                scrum_masters=scrum_masters,
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Handle POST request (optional, for saving updates)
    elif request.method == "POST":
        try:
            # Fetch project
            project = ProjectDetails.query.get_or_404(project_id)

            # Validations for project-level fields
            project_name = request.form.get("project_name", "").strip()
            if not project_name:
                flash("Project Name is required.", "error")
                return redirect(request.referrer)

            project_description = request.form.get("project_description", "").strip()
            if not project_description:
                flash("Project Description is required.", "error")
                return redirect(request.referrer)

            try:
                start_date = datetime.strptime(
                    request.form["start_date"], "%Y-%m-%d"
                ).date()
                end_date = datetime.strptime(
                    request.form["end_date"], "%Y-%m-%d"
                ).date()
                revised_end_date = datetime.strptime(
                    request.form["revised_end_date"], "%Y-%m-%d"
                ).date()

                if end_date < start_date:
                    flash("End Date cannot be earlier than Start Date.", "error")
                    return redirect(request.referrer)
                if revised_end_date < start_date:
                    flash(
                        "Revised End Date cannot be earlier than Start Date.", "error"
                    )
                    return redirect(request.referrer)
                status=request.form.get('status')
            except ValueError:
                flash("Invalid date format. Use YYYY-MM-DD.", "error")
                return redirect('/')

            # Update project-level details
            project.ProjectName = project_name
            project.ProjectDescription = project_description
            project.StartDate = start_date
            project.EndDate = end_date
            project.RevisedEndDate = revised_end_date
            project.Status=status
            db.session.commit()

            # Validate and update sprints
            for index, sprint in enumerate(project.sprints):
                sprint_no = request.form.get(f"sprintNo_{index+1}")
                if not sprint_no.isdigit():
                    flash(f"Sprint No for Sprint {index+1} must be a number.", "error")
                    return redirect(request.referrer)

                scrum_master_id = request.form.get(f"scrum_master_id_{index+1}")
                if not scrum_master_id:
                    flash(f"Scrum Master is required for Sprint {index+1}.", "error")
                    return redirect(request.referrer)

                try:
                    sprint_start_date = datetime.strptime(
                        request.form[f"sprint_start_date_{index+1}"], "%Y-%m-%d"
                    ).date()
                    sprint_end_date = datetime.strptime(
                        request.form[f"sprint_end_date_{index+1}"], "%Y-%m-%d"
                    ).date()

                    if sprint_end_date < sprint_start_date:
                        flash(
                            f"End Date cannot be earlier than Start Date for Sprint {index+1}.",
                            "error",
                        )
                        return redirect(request.referrer)
                except ValueError:
                    flash(
                        f"Invalid date format for Sprint {index+1}. Use YYYY-MM-DD.",
                        "error",
                    )
                    return redirect(request.referrer)

                velocity = request.form.get(f"sprint_velocity_{index+1}")
                if not velocity.isdigit() or int(velocity) <= 0:
                    flash(
                        f"Velocity for Sprint {index+1} must be a positive number.",
                        "error",
                    )
                    return redirect(request.referrer)

                # Update sprint details
                sprint.SprintNo = int(sprint_no)
                sprint.ScrumMasterID = int(scrum_master_id)
                sprint.StartDate = sprint_start_date
                sprint.EndDate = sprint_end_date
                sprint.Velocity = int(velocity)
                db.session.commit()

                # Validate and update user stories
                for user_story_index, user_story in enumerate(sprint.user_stories):
                    user_story_description = request.form.get(
                        f"story_desc_{index+1}_{user_story_index}", ""
                    ).strip()
                    if not user_story_description:
                        flash(
                            f"Description is required for User Story {user_story_index+1} in Sprint {index+1}.",
                            "error",
                        )
                        return redirect(request.referrer)

                    planned_sprint = request.form.get(
                        f"planned_sprint_{index+1}_{user_story_index}"
                    )
                    actual_sprint = request.form.get(
                        f"actual_sprint_{index+1}_{user_story_index}"
                    )

                    if not planned_sprint.isdigit() or not actual_sprint.isdigit():
                        flash(
                            f"Planned and Actual Sprint for User Story {user_story_index+1} in Sprint {index+1} must be numbers.",
                            "error",
                        )
                        return redirect(request.referrer)

                    story_point = request.form.get(
                        f"story_points_{index+1}_{user_story_index}"
                    )
                    if not story_point.isdigit() or int(story_point) <= 0:
                        flash(
                            f"Story Point for User Story {user_story_index+1} in Sprint {index+1} must be a positive number.",
                            "error",
                        )
                        return redirect(request.referrer)

                    moscow = request.form.get(
                        f"moscow_{index+1}_{user_story_index}", ""
                    ).strip()
                    if moscow not in [
                        "must-have",
                        "should-have",
                        "could-have",
                        "won't-have",
                    ]:
                        flash(
                            f"Invalid MOSCOW value for User Story {user_story_index+1} in Sprint {index+1}.",
                            "error",
                        )
                        return redirect(request.referrer)

                    assignee = request.form.get(
                        f"assignee_{index+1}_{user_story_index}", ""
                    ).strip()
                    if not assignee:
                        flash(
                            f"Assignee is required for User Story {user_story_index+1} in Sprint {index+1}.",
                            "error",
                        )
                        return redirect(request.referrer)

                    status = request.form.get(
                        f"status_{index+1}_{user_story_index}", ""
                    ).strip()
                    if status not in ["not-started", "in-progress", "completed"]:
                        flash(
                            f"Invalid status for User Story {user_story_index+1} in Sprint {index+1}.",
                            "error",
                        )
                        return redirect(request.referrer)

                    # Update user story
                    user_story.Description = user_story_description
                    user_story.PlannedSprint = int(planned_sprint)
                    user_story.ActualSprint = int(actual_sprint)
                    user_story.StoryPoint = int(story_point)
                    user_story.MOSCOW = moscow
                    user_story.Assignee = assignee
                    user_story.Status = status
                    db.session.commit()

            flash("Project successfully updated!", "success")
            return redirect(request.referrer)
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")
            return redirect(request.referrer)

    return render_template(
        "edit_project.html", project=project, scrum_masters=scrum_masters
    )


##### TEAM 3 ROUTES....

@app.route('/viewproject/<int:project_id>', methods=['GET'])
def viewproject(project_id):
    # Fetch project details using the passed project_id
    project = ProjectDetails.query.filter_by(ProjectId=project_id).first()  # Fetch project details
    if not project:
        # If the project is not found, handle the error (optional)
        return "Project not found", 404

    # Fetch user stories related to the specific project
    userstories_data = UserStories.query.filter_by(ProjectId=project_id).all()

    # Prepare the user stories data for the template
    userstories = [
        {
            "us_id": user_story.UserStoryID,
            "description": user_story.Description,
            "status": user_story.Status,
            "assignee": user_story.Assignee,
            "sprint": f"Sprint {user_story.SprintId}"  # Assuming SprintId is used for sprint number
        }
        for user_story in userstories_data
    ]

    # Fetch sprint calendar data related to the specific project
    sprints_data = SprintCalendar.query.filter_by(ProjectId=project_id).all()

    # Prepare the sprint calendar data for the template
    sprintcalendar= [
        {
            "sprint_no": sprint.SprintId,
            "start_date": sprint.StartDate.strftime('%b %d, %Y'),
            "end_date": sprint.EndDate.strftime('%b %d, %Y'),
            "velocity": sprint.Velocity
        }
        for sprint in sprints_data
    ]

    # Pass the project, user stories, and sprints to the template
    try:
        # Fetch data from the database
        sprints = SprintCalendar.query.all()
        projects = ProjectDetails.query.all()
        user_stories = UserStories.query.all()

        if not sprints or not projects:
            return render_template('charts.html', burn_down_url="", burn_up_url="", donut_chart_url="", velocity_chart_url="", sprint_progress_url="")

        # Fetch data from the database
        # Fetch data from the database
        team_performance_data = []

        # Loop through each Scrum Master (representing each team)
        for scrum_master in ScrumMasters.query.all():
            # Initialize counters for completed tasks and completed user stories
            completed_tasks = 0
            completed_user_stories = 0

            # Get all sprints for this Scrum Master
            for sprint in scrum_master.sprints:  # scrum_master.sprints refers to the sprints they are responsible for
                # Count the number of completed tasks for this sprint
                completed_tasks += db.session.query(Tasks) \
                    .filter(Tasks.UserStoryID == UserStories.UserStoryID,  # Correct join condition
                            UserStories.SprintId == sprint.SprintId,
                            Tasks.TaskStatus == 'Completed').count()

                # Count the number of completed user stories for this sprint
                completed_user_stories += db.session.query(UserStories) \
                    .filter(UserStories.SprintId == sprint.SprintId,
                            UserStories.Status == 'Completed').count()

            # Calculate average performance (mean of completed tasks and completed user stories)
            average_performance = (
                completed_tasks + completed_user_stories) / 2

            # Append the Scrum Master's performance data to the list
            team_performance_data.append({
                "Team": scrum_master.Name,  # Scrum Master Name as Team name
                "Completed Tasks": completed_tasks,
                "Completed User Stories": completed_user_stories,
                "Performance": average_performance  # Add performance data here
            })

        # If there's no performance data, render the empty chart page
        if not team_performance_data:
            return render_template('view.html', performance_chart_url="")

        # Create a DataFrame to visualize the performance data
        performance_df = pd.DataFrame(team_performance_data)

        sprint_data = {
            "Days": [sprint.SprintNo for sprint in sprints],
            "Sprint Estimated Effort (Down)": [sprint.Velocity for sprint in sprints],
            "Sprint Actual Effort (Down)": [sprint.Velocity * 0.85 for sprint in sprints],
            "Sprint Estimated Effort (Up)": [sprint.Velocity for sprint in sprints],
            "Sprint Actual Effort (Up)": [sprint.Velocity * 0.95 for sprint in sprints]
        }
        data = pd.DataFrame(sprint_data)

        # Burn-Down Chart
        cumulative_velocity = data['Sprint Estimated Effort (Down)'].cumsum()
        cumulative_actual_velocity = data['Sprint Actual Effort (Down)'].cumsum(
        )

        cumulative_effort_remaining = cumulative_velocity.max() - cumulative_velocity
        cumulative_actual_remaining = cumulative_velocity.max() - cumulative_actual_velocity

        plt.figure(figsize=(5, 5))
        plt.plot(data['Days'], cumulative_effort_remaining, marker='o',
                 linestyle='-', color='b', label='Estimated Effort Remaining')
        plt.plot(data['Days'], cumulative_actual_remaining, marker='s',
                 linestyle='--', color='r', label='Actual Effort Remaining')
        plt.title("Burn-Down Chart")
        plt.xlabel("Sprint Days")
        plt.ylabel("Effort Remaining")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        burn_down_url = base64.b64encode(img.getvalue()).decode()
        plt.close()

        # Burn-Up Chart
        plt.figure(figsize=(5, 5))
        plt.plot(data['Days'], cumulative_velocity, marker='o',
                 linestyle='-', color='g', label='Cumulative Estimated Effort')
        plt.plot(data['Days'], cumulative_actual_velocity, marker='s',
                 linestyle='--', color='orange', label='Cumulative Actual Effort')
        plt.title("Burn-Up Chart")
        plt.xlabel("Sprint Days")
        plt.ylabel("Effort Completed")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        burn_up_url = base64.b64encode(img.getvalue()).decode()
        plt.close()

        # Donut Chart
        status_counts = pd.Series(
            [project.Status for project in projects]).value_counts()
        labels = status_counts.index
        sizes = status_counts.values
        colors = ["#4CAF50", "#FF9800", "#F44336"]
        explode = (0.05,) * len(sizes)

        fig, ax = plt.subplots(figsize=(5, 5))
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
               colors=colors, explode=explode, wedgeprops={'edgecolor': 'white'})

        centre_circle = plt.Circle((0, 0), 0.70, fc='white')
        fig.gca().add_artist(centre_circle)
        plt.title('Project Status Distribution')
        plt.tight_layout()

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        donut_chart_url = base64.b64encode(img.getvalue()).decode()
        plt.close()

        # Velocity Chart
        sprint_numbers = [s.SprintNo for s in sprints]
        velocities = [s.Velocity for s in sprints]

        plt.figure(figsize=(5, 5))
        plt.bar(sprint_numbers, velocities, color="#2196F3", edgecolor="black")
        plt.xlabel("Sprint Number")
        plt.ylabel("Velocity")
        plt.title("Sprint Velocity Chart")
        plt.xticks(sprint_numbers)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        velocity_chart_url = base64.b64encode(img.getvalue()).decode()
        plt.close()

        # Sprint Progress Chart
        plt.figure(figsize=(5, 5))
        sprint_numbers = [s.SprintNo for s in sprints]
        progress = []

        for sprint in sprints:
            # Filter user stories for current sprint using SprintId
            user_stories_in_sprint = [us for us in user_stories
                                      if us.SprintId == sprint.SprintId]

            if user_stories_in_sprint:
                completed_stories = sum(1 for us in user_stories_in_sprint
                                        if us.Status == "completed")
                sprint_progress = (completed_stories /
                                   len(user_stories_in_sprint)) * 100
            else:
                sprint_progress = 0
            #print(sprint_progress)
            progress.append(sprint_progress)

        plt.plot(sprint_numbers, progress, marker='o', linestyle='-',
                 color='purple', label='Sprint Progress')
        plt.title("Sprint Progress Chart")
        plt.xlabel("Sprint Number")
        plt.ylabel("Progress (%)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        sprint_progress_url = base64.b64encode(img.getvalue()).decode()
        plt.close()

        # Performance Chart

        plt.figure(figsize=(8, 6))

        # Plot performance (Average of Completed Tasks and User Stories)
        plt.bar(performance_df['Team'], performance_df['Performance'],
                color='b', label='Performance', alpha=0.7)

        # Set titles and labels
        plt.title("Team Performance Chart")
        plt.xlabel("Scrum Master (Team)")
        plt.ylabel("Performance (Avg of Completed Tasks & User Stories)")
        plt.legend()
        plt.ylim(0, 2.5)
        plt.yticks([i * 0.5 for i in range(6)])
        # Adjust layout for better presentation
        plt.tight_layout()

        # Save the chart to a BytesIO object and encode it to Base64 for rendering
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        performance_chart_url = base64.b64encode(img.getvalue()).decode()

        # Close the plot
        plt.close()
    except Exception as e:
        return f"An error occurred: {e}", 500

    print(sprints)
    return render_template('view.html', userstories=userstories, project=project, sprints=sprintcalendar,
                           burn_down_url=burn_down_url,
                               burn_up_url=burn_up_url,
                               donut_chart_url=donut_chart_url,
                               velocity_chart_url=velocity_chart_url,
                               sprint_progress_url=sprint_progress_url,
                               performance_chart_url=performance_chart_url)

@app.route('/summary')
def summary():
    try:
        # Fetch data for summary
        projects = ProjectDetails.query.all()
        sprints = SprintCalendar.query.all()
        user_stories = UserStories.query.all()
        tasks = Tasks.query.all()

        # Aggregate project data
        project_summary = {
            "total_projects": len(projects),
            "completed_projects": sum(1 for p in projects if p.Status == "completed"),
            "active_projects": sum(1 for p in projects if p.Status == "active"),
            "pending_projects": sum(1 for p in projects if p.Status == "pending")
        }

        # Aggregate sprint data
        sprint_summary = {
            "total_sprints": len(sprints),
            "average_velocity": sum(s.Velocity for s in sprints) / len(sprints) if sprints else 0,
            "current_sprint": max(s.SprintNo for s in sprints) if sprints else None
        }

        # Aggregate user story data
        user_story_summary = {
            "total_user_stories": len(user_stories),
            "completed_stories": sum(1 for u in user_stories if u.Status == "Completed"),
            "in_progress_stories": sum(1 for u in user_stories if u.Status == "In Progress"),
            "pending_stories": sum(1 for u in user_stories if u.Status == "Pending")
        }

        # Aggregate task data
        task_summary = {
            "total_tasks": len(tasks),
            "completed_tasks": sum(1 for t in tasks if t.TaskStatus == "Completed"),
            "in_progress_tasks": sum(1 for t in tasks if t.TaskStatus == "In Progress"),
            "pending_tasks": sum(1 for t in tasks if t.TaskStatus == "Pending")
        }

        # Combine all summaries
        summary_data = {
            "projects": project_summary,
            "sprints": sprint_summary,
            "user_stories": user_story_summary,
            "tasks": task_summary
        }

        return render_template("summary.html", summary_data=summary_data)

    except Exception as e:
        return f"An error occurred while fetching the summary: {e}", 500
@app.route('/export-pdf')
def export_pdf():
    pass

@app.route('/submit', methods=['POST'])
def submit_project_data():
    try:
        data = request.json

        # Convert date strings to Python datetime.date objects
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        revised_end_date = (
            datetime.strptime(data['revised_end_date'], '%Y-%m-%d').date()
            if data.get('revised_end_date')
            else None
        )

        if start_date>=end_date:
            raise Exception("StartDate Cant Greater than EndDate")
        
        # Add Project
        new_project = ProjectDetails(
            ProductOwnerId = data['product_owner_id'],
            ProjectName = data['project_name'],
            ProjectDescription = data['project_description'],
            StartDate = start_date,
            EndDate = end_date,
            RevisedEndDate = revised_end_date,
            Status = data['status']
        )
        
        
        db.session.add(new_project)
        db.session.commit()
        print("1st successfull")
        last_project = ProjectDetails.query.order_by(ProjectDetails.ProjectId.desc()).first()
        last_project_id = last_project.ProjectId if last_project else None

        selected_user_id = data['selected_user_ids'].split(',')
        for i in range(len(selected_user_id)):
            new_project_user = ProjectUsers(
                UserID = selected_user_id[i],
                ProjectId = last_project_id
            )
            db.session.add(new_project_user)
            db.session.commit()

        #sprint_no
        i = 1
        # Add Sprints and User Stories
        for sprint in data['sprints']:
            sprint_start_date = datetime.strptime(sprint['start_date'], '%Y-%m-%d').date()
            sprint_end_date = datetime.strptime(sprint['end_date'], '%Y-%m-%d').date()



            new_sprint = SprintCalendar(
                ProjectId = last_project_id,
                SprintNo = i,
                ScrumMasterID = sprint['scrum_master_id'],
                StartDate = sprint_start_date,
                EndDate = sprint_end_date,
                Velocity = sprint['velocity']

            )
            i+=1
            db.session.add(new_sprint)
            db.session.commit()
            print("2nd successfull")

            for story in sprint['user_stories']:
                last_sprint = SprintCalendar.query.order_by(SprintCalendar.SprintId.desc()).first()
                last_sprint_id = last_sprint.SprintId if last_sprint else None
                new_story = UserStories(
                        ProjectId = last_project_id,
                        SprintId = last_sprint_id,
                        PlannedSprint = story['planned_sprint'],
                        ActualSprint = story['actual_sprint'],
                        Description = story['description'],
                        StoryPoint = story['story_points'],
                        MOSCOW = story['moscow'],
                        Assignee = story['assignee'],
                        Status = story['status']
                )
                db.session.add(new_story)
                db.session.commit()
                print("3rd successfull")

        return jsonify({"message": "Project, sprints, and user stories added successfully."}), 201

    except Exception as e:
        db.session.rollback()
        print("Full error traceback:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400



if __name__ == "__main__":
    # app = create_app()
    app.run(debug=True, port=5002)
