from flask_restx import Namespace, Resource, fields

api = Namespace("Products", description="Product management")

product_model = api.model("Product", {
    "id": fields.Integer(),
    "name": fields.String(),
    "price": fields.Float(),
})

@api.route("/<int:id>")
class ProductResource(Resource):
    @api.marshal_with(product_model)
    def get(self, id):
        """Get product by ID"""
        return {"id": id, "name": "Sample Product", "price": 99.99}
