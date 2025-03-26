from flask_restx import Namespace, Resource, fields
from flask import request
from app.services.standard_service import create_standard, get_standard_by_id, get_all_standards, update_standard, delete_standard

api = Namespace("Standards", description="Standard management")

standard_model = api.model("Standard", {
    "id": fields.Integer(readOnly=True),
    "name": fields.String(required=True, description="Standard name"),
    "description": fields.String(description="Detailed description"),
})

@api.route("/")
class StandardList(Resource):
    @api.marshal_list_with(standard_model)
    def get(self):
        return get_all_standards()

    @api.expect(standard_model)
    @api.marshal_with(standard_model, code=201)
    def post(self):
        data = request.json
        return create_standard(data), 201

@api.route("/<int:id>")
class StandardResource(Resource):
    @api.marshal_with(standard_model)
    def get(self, id):
        return get_standard_by_id(id)

    @api.expect(standard_model)
    @api.marshal_with(standard_model)
    def put(self, id):
        data = request.json
        return update_standard(id, data)

    def delete(self, id):
        delete_standard(id)
        return {"message": "Standard deleted"}, 204
