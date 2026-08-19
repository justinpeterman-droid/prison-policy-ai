"""Authorization rules shared by browser and future admin paperwork routes."""


def can_read_paperwork(actor, record) -> bool:
    return (
        actor.role == "admin"
        or record.created_by_staff_member_id == actor.staff_member_id
    )


def can_edit_paperwork(actor, record) -> bool:
    return can_read_paperwork(actor, record)
