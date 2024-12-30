from flask import Flask, redirect, url_for, render_template, flash, jsonify, request
from routers.team1 import login_bp, login_manager,track_login, track_logout  # Import the auth blueprint
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
from datetime import datetime
import send_mail as sm
from flask_login import user_logged_in, user_logged_out


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

# Connect signals
user_logged_in.connect(track_login, app)
user_logged_out.connect(track_logout, app)


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
    print(projects_data)
    total_projects = ProjectDetails.query.count()
    active_projects = ProjectDetails.query.filter_by(Status="active").count()
    on_hold_projects = ProjectDetails.query.filter_by(Status="On Hold").count()
    user_name = Users.query.filter_by(Email="john.admin@example.com").first().Name


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
        user_name=user_name
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
    sprints = [
        {
            "sprint_no": sprint.SprintId,
            "start_date": sprint.StartDate.strftime('%b %d, %Y'),
            "end_date": sprint.EndDate.strftime('%b %d, %Y'),
            "velocity": sprint.Velocity
        }
        for sprint in sprints_data
    ]

    # Pass the project, user stories, and sprints to the template
    return render_template('view.html', userstories=userstories, project=project, sprints=sprints)


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
    app.run(debug=True)
