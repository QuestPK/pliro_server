from app.models.project_model import ProjectModel
from app.extensions import db

def create_project(data):
    new_project = ProjectModel(**data)
    db.session.add(new_project)
    db.session.commit()
    return new_project

def get_project_by_id(project_id):
    return ProjectModel.query.get_or_404(project_id)

def get_all_projects():
    return ProjectModel.query.all()

def update_project(project_id, data):
    project = get_project_by_id(project_id)
    for key, value in data.items():
        setattr(project, key, value)
    db.session.commit()
    return project

def delete_project(project_id):
    project = get_project_by_id(project_id)
    db.session.delete(project)
    db.session.commit()
