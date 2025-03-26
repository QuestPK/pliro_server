from app.models.standard_model import Standard
from app.extensions import db

def create_standard(data):
    standard = Standard(**data)
    db.session.add(standard)
    db.session.commit()
    return standard

def get_standard_by_id(standard_id):
    return Standard.query.get_or_404(standard_id)

def get_all_standards():
    return Standard.query.all()

def update_standard(standard_id, data):
    standard = get_standard_by_id(standard_id)
    for key, value in data.items():
        setattr(standard, key, value)
    db.session.commit()
    return standard

def delete_standard(standard_id):
    standard = get_standard_by_id(standard_id)
    db.session.delete(standard)
    db.session.commit()
