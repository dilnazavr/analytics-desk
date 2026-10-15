from app import create_app, db
from app.models import *  # noqa

app = create_app()

@app.cli.command("seed")
def seed():
    """Create initial roles and demo user."""
    from app.models.user import Role, User
    from app.models.case import Case, CaseMember
    from datetime import date

    if Role.query.count() == 0:
        roles = [
            Role(name="analyst", description="Аналитик"),
            Role(name="senior_analyst", description="Старший аналитик"),
            Role(name="manager", description="Руководитель"),
            Role(name="admin", description="Администратор"),
        ]
        db.session.add_all(roles)
        db.session.commit()
        print("Roles created")

    admin_role = Role.query.filter_by(name="admin").first()
    analyst_role = Role.query.filter_by(name="analyst").first()

    if not User.query.filter_by(email="admin@analytics.local").first():
        u = User(
            email="admin@analytics.local",
            full_name="Администратор Системы",
            role_id=admin_role.id,
            is_active=True,
        )
        u.set_password("admin123")
        db.session.add(u)
        print("Admin user created: admin@analytics.local / admin123")

    if not User.query.filter_by(email="analyst@analytics.local").first():
        u = User(
            email="analyst@analytics.local",
            full_name="Иванов Иван Иванович",
            role_id=analyst_role.id,
            is_active=True,
        )
        u.set_password("analyst123")
        db.session.add(u)
        print("Analyst user created: analyst@analytics.local / analyst123")

    db.session.commit()

    # Demo case
    analyst = User.query.filter_by(email="analyst@analytics.local").first()
    if Case.query.count() == 0 and analyst:
        c = Case(
            number="AD-2026-0001",
            title="Анализ приобретения и реализации (демо)",
            organization_name='ТОО «Демо Компания»',
            bin="123456789012",
            basis="Поручение № 01 от 01.01.2026",
            basis_date=date(2026, 1, 1),
            requesting_body="Управление превенции",
            subject="Анализ оборотов за 2025 год",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
            responsible_id=analyst.id,
            status="open",
            created_by_id=analyst.id,
        )
        db.session.add(c)
        db.session.flush()
        db.session.add(CaseMember(case_id=c.id, user_id=analyst.id, role_in_case="analyst"))
        db.session.commit()
        print("Demo case created")

    print("Seed completed")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
