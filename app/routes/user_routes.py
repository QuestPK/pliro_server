from flask_restx import Namespace, Resource, fields
from flask import request
from app.extensions import firebase_auth

api = Namespace("Users", description="User authentication")

user_model = api.model("User", {
    "id": fields.Integer(),
    "email": fields.String(),
    "token": fields.String(),
})

@api.route("/verify")
class VerifyUser(Resource):
    @api.expect(user_model)
    def post(self):
        """Verify Firebase user token"""
        data = request.json
        try:
            user = firebase_auth.verify_token(data["token"])
            return {"message": "Verified", "uid": user["uid"]}
        except Exception as e:
            return {"error": str(e)}, 401
