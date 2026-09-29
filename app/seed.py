from decimal import Decimal

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Centre, CentreTest, DiagnosticTest

TESTS = ["CBC", "Lipid Profile", "HbA1c", "Thyroid Panel", "Vitamin D"]
CENTRES = {
    "EVE Diagnostics Noida": ("Noida", {"CBC": 300, "Lipid Profile": 600, "HbA1c": 450}),
    "EVE Diagnostics Delhi": ("Delhi", {"CBC": 350, "Thyroid Panel": 500, "Vitamin D": 900}),
    "EVE Diagnostics Gurugram": ("Gurugram", {"CBC": 320, "Lipid Profile": 650, "Vitamin D": 850}),
}


def seed():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(Centre).limit(1)):
            print("Already seeded")
            return
        tests = {name: DiagnosticTest(name=name) for name in TESTS}
        db.add_all(tests.values())
        for name, (location, prices) in CENTRES.items():
            centre = Centre(name=name, location=location)
            db.add(centre)
            for test_name, price in prices.items():
                db.add(CentreTest(centre=centre, test=tests[test_name], price=Decimal(price)))
        db.commit()
        print("Seeded")


if __name__ == "__main__":
    seed()