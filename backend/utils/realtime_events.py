def metadata_changed_payload(resource, action, item_id=None, department_id=None):
    payload = {
        "resource": resource,
        "action": action,
    }
    if item_id:
        payload["id"] = item_id
    if department_id:
        payload["department_id"] = department_id
    return payload
