from flask import Flask, redirect, url_for, render_template, flash, jsonify, request
from routers.team1 import login_bp, login_manager  # Import the auth blueprint
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
)
from email.message import EmailMessage
import smtplib
from datetime import datetime




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
app.config["SQLALCHEMY_ECHO"] = True

# Initialize extensions
db.init_app(app)

# Register the auth blueprint with the url_prefix 'auth'
app.register_blueprint(login_bp, url_prefix="/auth")


# Create tables if necessary
with app.app_context():
    db.create_all()


# Dashboard Logic
@app.route("/")
def projects():
    projects_data = ProjectDetails.query.all()
    total_projects = ProjectDetails.query.count()
    active_projects = ProjectDetails.query.filter_by(Status="active").count()
    on_hold_projects = ProjectDetails.query.filter_by(Status="On Hold").count()

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
    return jsonify([{"id": user.UserID, "name": user.Username} for user in users])


@app.route("/addproject")
def addproject():
    return render_template("index.html")


# Mail Sending
def send_emails_to_users(email_list, project_name, proj_desc, roles):
    sender_email = "sukheshdasari@gmail.com"
    sender_password = "drer ssxn yxuk xwlz"  # Use your app password here
    subject = "Project Assignment Notification"

    try:
        for recipient_email, role in zip(email_list, roles):
            msg = EmailMessage()
            body_template = (
                f"Hello,\n\nYou have assigned {role},\n\n"
                f"You have been assigned to a new project: {project_name}.\n"
                "Please log in to the system for more details.\n\n"
                f"Description of project:{proj_desc}\n\n"
                "Regards,\nProject Management Team"
            )
            msg["From"] = sender_email
            msg["To"] = recipient_email
            msg["Subject"] = subject
            msg.set_content(body_template)

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)

            print(f"Email sent to {recipient_email}!")

    except Exception as e:
        print(f"Failed to send email: {e}")


# Submission of Form
@app.route("/submit", methods=["POST"])
def submit_project_data():
    try:
        data = request.json

        # Validate Product Owner ID
        if not data.get("product_owner_id") or not isinstance(
            data["product_owner_id"], int
        ):
            flash("Valid Product Owner ID is required.", "error")
            return redirect(request.referrer)
        product_owner = ProductOwner.query.get(data["product_owner_id"])
        if not product_owner:
            flash("Product Owner not found.", "error")
            return redirect(request.referrer)

        # Validate Project Name
        if not data.get("project_name") or len(data["project_name"].strip()) == 0:
            flash("Project Name is required.", "error")
            return redirect(request.referrer)

        # Validate Project Description
        if (
            not data.get("project_description")
            or len(data["project_description"].strip()) == 0
        ):
            flash("Project Description is required.", "error")
            return redirect(request.referrer)

        # Validate Dates
        try:
            start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
            end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
            revised_end_date = (
                datetime.strptime(data["revised_end_date"], "%Y-%m-%d").date()
                if data.get("revised_end_date")
                else None
            )
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "error")
            return redirect(request.referrer)

        if start_date >= end_date:
            flash("Start date cannot be greater than or equal to end date.", "error")
            return redirect(request.referrer)

        # Validate Status
        if data.get("status") not in ["Active", "Completed", "On Hold", "Cancelled"]:
            flash(
                "Invalid status. Must be one of: Active, Completed, or Pending.",
                "error",
            )
            return redirect(request.referrer)

        # Add Project
        new_project = ProjectDetails(
            ProductOwnerId=data["product_owner_id"],
            ProjectName=data["project_name"],
            ProjectDescription=data["project_description"],
            StartDate=start_date,
            EndDate=end_date,
            RevisedEndDate=revised_end_date,
            Status=data["status"],
        )
        db.session.add(new_project)
        db.session.commit()

        # Validate Selected User IDs
        if not data.get("selected_user_ids"):
            flash("At least one user must be selected.", "error")
            return redirect(request.referrer)

        selected_user_ids = data["selected_user_ids"].split(",")
        user_emails = []

        for user_id in selected_user_ids:
            if not user_id.isdigit():
                flash(f"Invalid User ID: {user_id}.", "error")
                return redirect(request.referrer)
            user = Users.query.get(int(user_id))
            if not user:
                flash(f"User with ID {user_id} not found.", "error")
                return redirect(request.referrer)
            user_emails.append(user.Email)
            new_project_user = ProjectUsers(
                UserID=user.UserID, ProjectId=new_project.ProjectId
            )
            db.session.add(new_project_user)

        # Send emails to product owner and team members
        send_emails_to_users(
            [product_owner.Email] + user_emails,
            data["project_name"],
            data["project_description"],
            ["Product Owner"] + ["Team Member"] * len(user_emails),
        )

        # Validate and Add Sprints
        for i, sprint in enumerate(data["sprints"], start=1):
            try:
                sprint_start_date = datetime.strptime(
                    sprint["start_date"], "%Y-%m-%d"
                ).date()
                sprint_end_date = datetime.strptime(
                    sprint["end_date"], "%Y-%m-%d"
                ).date()
            except ValueError:
                flash(f"Invalid date format for Sprint {i}. Use YYYY-MM-DD.", "error")
                return redirect(request.referrer)

            if sprint_start_date >= sprint_end_date:
                flash(
                    f"Sprint {i} start date cannot be greater than or equal to the end date.",
                    "error",
                )
                return redirect(request.referrer)

            if not sprint.get("scrum_master_id") or not isinstance(
                sprint["scrum_master_id"], int
            ):
                flash(f"Valid Scrum Master ID is required for Sprint {i}.", "error")
                return redirect(request.referrer)
            scrum_master = ScrumMasters.query.get(sprint["scrum_master_id"])
            if not scrum_master:
                flash(
                    f"Scrum Master with ID {sprint['scrum_master_id']} not found.",
                    "error",
                )
                return redirect(request.referrer)

            new_sprint = SprintCalendar(
                ProjectId=new_project.ProjectId,
                SprintNo=i,
                ScrumMasterID=sprint["scrum_master_id"],
                StartDate=sprint_start_date,
                EndDate=sprint_end_date,
                Velocity=sprint.get("velocity", 0),
            )
            db.session.add(new_sprint)
            db.session.commit()

            # Validate and Add User Stories
            for j, story in enumerate(sprint["user_stories"], start=1):
                if (
                    not story.get("description")
                    or len(story["description"].strip()) == 0
                ):
                    flash(
                        f"Description is required for User Story {j} in Sprint {i}.",
                        "error",
                    )
                    return redirect(request.referrer)
                if not story.get("planned_sprint") or not isinstance(
                    story["planned_sprint"], int
                ):
                    flash(
                        f"Valid Planned Sprint is required for User Story {j} in Sprint {i}.",
                        "error",
                    )
                    return redirect(request.referrer)
                if not story.get("actual_sprint") or not isinstance(
                    story["actual_sprint"], int
                ):
                    flash(
                        f"Valid Actual Sprint is required for User Story {j} in Sprint {i}.",
                        "error",
                    )
                    return redirect(request.referrer)
                if story.get("moscow") not in [
                    "Must Have",
                    "Should Have",
                    "Could Have",
                    "Won't Have",
                ]:
                    flash(
                        f"Invalid MoSCoW priority for User Story {j} in Sprint {i}.",
                        "error",
                    )
                    return redirect(request.referrer)
                if not story.get("assignee"):
                    flash(
                        f"Assignee is required for User Story {j} in Sprint {i}.",
                        "error",
                    )
                    return redirect(request.referrer)

                new_story = UserStories(
                    ProjectId=new_project.ProjectId,
                    SprintId=new_sprint.SprintId,
                    PlannedSprint=story["planned_sprint"],
                    ActualSprint=story["actual_sprint"],
                    Description=story["description"],
                    StoryPoint=story.get("story_points", 0),
                    MOSCOW=story["moscow"],
                    Assignee=story["assignee"],
                    Status=story.get("status", "Pending"),
                )
                db.session.add(new_story)

        db.session.commit()
        flash("Project, sprints, and user stories added successfully.", "success")
        return jsonify({"message": "Project added successfully."}), 201

    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(request.referrer)


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
            except ValueError:
                flash("Invalid date format. Use YYYY-MM-DD.", "error")
                return redirect(request.referrer)

            # Update project-level details
            project.ProjectName = project_name
            project.ProjectDescription = project_description
            project.StartDate = start_date
            project.EndDate = end_date
            project.RevisedEndDate = revised_end_date

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
            return redirect("/")

    return render_template(
        "edit_project.html", project=project, scrum_masters=scrum_masters
    )


if __name__ == "__main__":
    # app = create_app()
    app.run(debug=True)
