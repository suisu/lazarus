
def create_or_update(session, model, new_values={}, filter_by={}, commit=True, ):
    if bool(filter_by):
        instance = session.query(model).filter_by(**filter_by).one_or_none()
    if instance:
        session.delete(instance)
        session.commit()
        
    new_values |= {}
    instance = model(**new_values)
    try:
        session.add(instance)
        if commit:
            session.commit()
    except Exception: 
        session.rollback()
        instance = session.query(model).filter_by(**new_values).one()
        return instance, False
    else:
        return instance, True
