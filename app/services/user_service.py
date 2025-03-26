from app.models.user_model import User
from app.extensions import db

def create_user(data):
    user = User(name=data["name"], email=data["email"])
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    return user

def get_user_by_id(user_id):
    return User.query.get_or_404(user_id)

def get_all_users():
    return User.query.all()

def update_user(user_id, data):
    user = get_user_by_id(user_id)
    for key, value in data.items():
        if key == "password":
            user.set_password(value)
        else:
            setattr(user, key, value)
    db.session.commit()
    return user

def delete_user(user_id):
    user = get_user_by_id(user_id)
    db.session.delete(user)
    db.session.commit()
