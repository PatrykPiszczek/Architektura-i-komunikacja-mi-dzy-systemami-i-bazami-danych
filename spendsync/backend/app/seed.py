from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import select

from .auth import hash_password
from .database import Base, SessionLocal, engine
from .models import Budget, Category, Expense, User

DEMO_EMAIL = "demo@spendsync.pl"
DEMO_PASSWORD = "demo1234"


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == DEMO_EMAIL)):
            print("Demo data already present, skipping.")
            return

        user = User(
            email=DEMO_EMAIL,
            display_name="Demo User",
            password_hash=hash_password(DEMO_PASSWORD),
        )
        db.add(user)
        db.flush()

        palette = {
            "Jedzenie": "#ef4444",
            "Transport": "#3b82f6",
            "Rozrywka": "#a855f7",
            "Rachunki": "#f59e0b",
        }
        categories = {}
        for name, color in palette.items():
            category = Category(user_id=user.id, name=name, color=color)
            db.add(category)
            db.flush()
            categories[name] = category

        today = date.today()
        sample = [
            ("Jedzenie", 24.50, "Lunch w mieście", 1),
            ("Jedzenie", 156.30, "Zakupy spożywcze", 3),
            ("Transport", 4.60, "Bilet autobusowy", 1),
            ("Transport", 220.00, "Tankowanie", 5),
            ("Rozrywka", 45.00, "Kino", 2),
            ("Rachunki", 89.99, "Internet", 6),
            ("Rachunki", 320.00, "Prąd", 8),
        ]
        for category_name, amount, description, days_ago in sample:
            db.add(
                Expense(
                    user_id=user.id,
                    client_uuid=str(uuid4()),
                    category_id=categories[category_name].id,
                    amount=amount,
                    currency="PLN",
                    description=description,
                    spent_at=today - timedelta(days=days_ago),
                )
            )

        db.add(
            Budget(
                user_id=user.id,
                category_id=categories["Jedzenie"].id,
                period=today.strftime("%Y-%m"),
                limit_amount=600.00,
            )
        )

        db.commit()
        print(f"Seeded demo account: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
