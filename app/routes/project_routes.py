from flask_restx import Namespace, Resource, fields
from flask import request
from app.services.project_service import create_project, get_project_by_id, get_all_projects, update_project, delete_project

api = Namespace("Projects", description="Project management")

# Model for API documentation
project_model = api.model("Project", {
    "id": fields.Integer(readOnly=True),
    "name": fields.String(required=True, description="Project name"),
    "use": fields.String(description="Project use case"),
    "description": fields.String(description="Detailed description"),
    "dimensions": fields.String(description="Project dimensions"),
    "weight": fields.String(description="Project weight"),
    "regions": fields.List(fields.String, description="Supported regions"),
    "countries": fields.List(fields.String, description="Supported countries"),
    "technical_details": fields.Raw(description="Technical details in JSON format"),
    "multi_variant": fields.Boolean(description="Has multiple variants"),
    "pre_certified_components": fields.Boolean(description="Uses pre-certified components"),
    "user_id": fields.Integer(description="Owner User ID"),
})

@api.route("/")
class ProjectList(Resource):
    @api.marshal_list_with(project_model)
    def get(self):
        return get_all_projects()

    @api.expect(project_model)
    @api.marshal_with(project_model, code=201)
    def post(self):
        data = request.json
        return create_project(data), 201

@api.route("/<int:id>")
class ProjectResource(Resource):
    @api.marshal_with(project_model)
    def get(self, id):
        return get_project_by_id(id)

    @api.expect(project_model)
    @api.marshal_with(project_model)
    def put(self, id):
        data = request.json
        return update_project(id, data)

    def delete(self, id):
        delete_project(id)
        return {"message": "Project deleted"}, 204
