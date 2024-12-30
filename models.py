from database import db

# ProductOwner Table
class ProductOwner(db.Model):
    __tablename__ = 'product_owner'  # Added table name
    ProductOwnerId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(255), nullable=False)
    Email = db.Column(db.String(255), unique=True, nullable=False)
    RoleName = db.Column(db.String(255), nullable=False)

    # Relationships
    projects = db.relationship('ProjectDetails', backref='product_owner', lazy=True)

    def __repr__(self):
        return f"<ProductOwner {self.Name}>"

# ProjectDetails Table
class ProjectDetails(db.Model):
    __tablename__ = 'project_details'
    ProjectId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ProductOwnerId = db.Column(db.Integer, db.ForeignKey('product_owner.ProductOwnerId'), nullable=False)
    ProjectName = db.Column(db.String(255), nullable=False, unique=True)  # Added unique constraint
    ProjectDescription = db.Column(db.Text)
    StartDate = db.Column(db.Date, nullable=False)
    EndDate = db.Column(db.Date, nullable=False)
    RevisedEndDate = db.Column(db.Date)
    Status = db.Column(db.String(100), default="Not Started")

    # Relationships
    sprints = db.relationship('SprintCalender', backref='project', lazy=True)
    user_stories = db.relationship('UserStories', backref='project', lazy=True)

    def __repr__(self):
        return f"<ProjectDetails {self.ProjectName}>"

# SprintCalender Table
class SprintCalender(db.Model):
    __tablename__ = 'sprint_calender'
    SprintId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ProjectId = db.Column(db.Integer, db.ForeignKey('project_details.ProjectId'), nullable=False)
    ScrumMasterID = db.Column(db.Integer, db.ForeignKey('scrum_masters.ScrumMasterID'), nullable=True)
    SprintNo = db.Column(db.Integer, nullable=True)
    StartDate = db.Column(db.Date, nullable=False)
    EndDate = db.Column(db.Date, nullable=False)
    Velocity = db.Column(db.Integer, default=0)

    # Relationships
    scrum_master = db.relationship('ScrumMasters', backref='sprints')
    user_stories = db.relationship('UserStories', backref='sprint', lazy=True)

    def __repr__(self):
        return f"<SprintCalender Sprint {self.SprintNo}>"

# ScrumMasters Table
class ScrumMasters(db.Model):
    __tablename__ = 'scrum_masters'
    ScrumMasterID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Email = db.Column(db.String(255), nullable=False, unique=True)
    Name = db.Column(db.String(255), nullable=False)
    ContactNumber = db.Column(db.String(15))

    def __repr__(self):
        return f"<ScrumMasters {self.Name}>"

# Users Table
class Users(db.Model):
    __tablename__ = 'users'
    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserName = db.Column(db.String(50), nullable=False)
    Password = db.Column(db.String(100), nullable=False)
    Email = db.Column(db.String(100), unique=True, nullable=False)
    Name = db.Column(db.String(100), nullable=False)
    DOB = db.Column(db.Date, nullable=True)
    Role = db.Column(db.String(50), nullable=True)
    PhoneNumber = db.Column(db.String(15), unique=True, nullable=True)
    approved = db.Column(db.Boolean, default=False)

    # Relationships
    tasks = db.relationship('Tasks', backref='assigned_user', lazy=True)
    roles = db.relationship('UserRoles', backref='user', lazy=True)

    def __repr__(self):
        return f"<Users {self.UserName}>"

# Tasks Table
class Tasks(db.Model):
    __tablename__ = 'tasks'
    TaskId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserStoryID = db.Column(db.Integer, db.ForeignKey('user_stories.UserStoryID'), nullable=False)
    TaskName = db.Column(db.String(255), nullable=False)
    AssignedUserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    TaskStatus = db.Column(db.String(100), default="Not Started")

    # Relationships
    user_story = db.relationship('UserStories', backref='tasks')

    def __repr__(self):
        return f"<Tasks {self.TaskName}>"

# UserRoles Table
class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    RoleID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    RoleName = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<UserRoles {self.RoleName}>"

# UserStories Table
class UserStories(db.Model):
    __tablename__ = 'user_stories'
    UserStoryID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ProjectId = db.Column(db.Integer, db.ForeignKey('project_details.ProjectId'), nullable=False)
    SprintId = db.Column(db.Integer, db.ForeignKey('sprint_calender.SprintId'), nullable=True)
    PlannedSprint = db.Column(db.Integer, nullable=False)
    ActualSprint = db.Column(db.Integer, nullable=False)
    Description = db.Column(db.Text, nullable=False)
    StoryPoints = db.Column(db.Integer, nullable=False)
    MOSCOW = db.Column(db.String(50), nullable=False)
    Dependency = db.Column(db.String(255))
    Assignee = db.Column(db.String(255))
    Status = db.Column(db.String(100), default="Not Started")

    def __repr__(self):
        return f"<UserStories {self.Description[:20]}>"

# ProjectUsers Table
class ProjectUsers(db.Model):
    __tablename__ = 'ProjectUsers'

    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), primary_key=True, nullable=False)
    ProjectId = db.Column(db.Integer, db.ForeignKey('project_details.ProjectId'), primary_key=True, nullable=False)

    # Relationships (optional, for convenience in accessing related objects)
    user = db.relationship('Users', backref='project_associations')
    project = db.relationship('ProjectDetails', backref='user_associations')

    def __repr__(self):
        return f"<ProjectUsers(UserID={self.UserID}, ProjectId={self.ProjectId})>"

