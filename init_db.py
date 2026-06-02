"""
Script d'initialisation : crée la BDD, les tables, et un tenant + utilisateur admin de démonstration.
Lancer une seule fois : python init_db.py
"""
from app import create_app, db
from app.models.tenant import Tenant
from app.models.user   import User

app = create_app('development')

with app.app_context():
    db.create_all()
    print("Tables créées.")

    # Vérifier si déjà initialisé
    if Tenant.query.first():
        print("Base déjà initialisée.")
    else:
        tenant = Tenant(
            nom       = 'Téranga Conseil',
            ninea     = '005 432 1098',
            email     = 'contact@teranga-conseil.sn',
            plan      = 'pro',
            nb_sieges = 5,
        )
        db.session.add(tenant)
        db.session.flush()

        admin = User(
            tenant_id = tenant.id,
            nom       = 'Diop',
            prenom    = 'Aminata',
            email     = 'a.diop@teranga-conseil.sn',
            role      = 'admin',
        )
        admin.set_password('sengestion2026')
        db.session.add(admin)
        db.session.commit()

        print("Tenant 'Téranga Conseil' et utilisateur admin créés.")
        print("Email    : a.diop@teranga-conseil.sn")
        print("Password : sengestion2026")
