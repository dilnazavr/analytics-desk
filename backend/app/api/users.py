from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User, Role
from app.models.audit import AuditLog

users_bp = Blueprint("users", __name__)


def _current_user():
    uid = int(get_jwt_identity())
    return User.query.get(uid)


def _require_admin():
    user = _current_user()
    if not user or not user.role or user.role.name != "admin":
        return None
    return user


@users_bp.route("", methods=["GET"])
@jwt_required()
def list_users():
    if not _require_admin():
        return jsonify({"error": "Только администратор"}), 403
    users = User.query.order_by(User.id).all()
    return jsonify([u.to_dict() for u in users])


@users_bp.route("/roles", methods=["GET"])
@jwt_required()
def list_roles():
    if not _require_admin():
        return jsonify({"error": "Только администратор"}), 403
    return jsonify([r.to_dict() for r in Role.query.order_by(Role.id).all()])


@users_bp.route("", methods=["POST"])
@jwt_required()
def create_user():
    admin = _require_admin()
    if not admin:
        return jsonify({"error": "Только администратор"}), 403
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    full_name = (data.get("full_name") or "").strip()
    password = data.get("password") or ""
    role_name = data.get("role") or "analyst"
    if not email or not full_name or len(password) < 6:
        return jsonify({"error": "Нужны email, ФИО и пароль (мин. 6 символов)"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email уже занят"}), 400
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        role = Role.query.filter_by(name="analyst").first()
    if not role:
        return jsonify({"error": "Роль не найдена"}), 400
    u = User(email=email, full_name=full_name, role_id=role.id, is_active=True)
    u.set_password(password)
    db.session.add(u)
    db.session.add(AuditLog(
        user_id=admin.id, action="user_created", entity_type="user",
        details={"email": email, "role": role.name},
    ))
    db.session.commit()
    return jsonify(u.to_dict()), 201


@users_bp.route("/<int:user_id>", methods=["PATCH"])
@jwt_required()
def update_user(user_id):
    admin = _require_admin()
    if not admin:
        return jsonify({"error": "Только администратор"}), 403
    u = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    if "full_name" in data and data["full_name"]:
        u.full_name = data["full_name"].strip()
    if "email" in data and data["email"]:
        email = data["email"].strip().lower()
        other = User.query.filter_by(email=email).first()
        if other and other.id != u.id:
            return jsonify({"error": "Email уже занят"}), 400
        u.email = email
    if "is_active" in data:
        if u.id == admin.id and not data["is_active"]:
            return jsonify({"error": "Нельзя отключить самого себя"}), 400
        u.is_active = bool(data["is_active"])
    if "role" in data and data["role"]:
        role = Role.query.filter_by(name=data["role"]).first()
        if role:
            u.role_id = role.id
    if data.get("password"):
        if len(data["password"]) < 6:
            return jsonify({"error": "Пароль мин. 6 символов"}), 400
        u.set_password(data["password"])
    db.session.add(AuditLog(
        user_id=admin.id, action="user_updated", entity_type="user", entity_id=u.id,
        details={k: ("***" if k == "password" else data[k]) for k in data},
    ))
    db.session.commit()
    return jsonify(u.to_dict())


@users_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    admin = _require_admin()
    if not admin:
        return jsonify({"error": "Только администратор"}), 403
    if user_id == admin.id:
        return jsonify({"error": "Нельзя удалить самого себя"}), 400
    u = User.query.get_or_404(user_id)
    email = u.email
    db.session.delete(u)
    db.session.add(AuditLog(
        user_id=admin.id, action="user_deleted", entity_type="user", entity_id=user_id,
        details={"email": email},
    ))
    db.session.commit()
    return jsonify({"ok": True})
