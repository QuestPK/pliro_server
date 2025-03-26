from flask_restx import Namespace, Resource, fields
from flask import request
from app.services.user_service import create_user, get_user_by_id, get_all_users, update_user, delete_user

api = Namespace("Users", description="User management")

user_model = api.model("User", {
    "id": fields.Integer(readOnly=True),
    "name": fields.String(required=True, description="User name"),
    "email": fields.String(required=True, description="User email"),
    "password": fields.String(required=True, description="User password", min_length=6),
})

@api.route("/")
class UserList(Resource):
    @api.marshal_list_with(user_model)
    def get(self):
        return get_all_users()

    @api.expect(user_model)
    @api.marshal_with(user_model, code=201)
    def post(self):
        data = request.json
        return create_user(data), 201

@api.route("/<int:id>")
class UserResource(Resource):
    @api.marshal_with(user_model)
    def get(self, id):
        return get_user_by_id(id)

    @api.expect(user_model)
    @api.marshal_with(user_model)
    def put(self, id):
        data = request.json
        return update_user(id, data)

    def delete(self, id):
        delete_user(id)
        return {"message": "User deleted"}, 204
