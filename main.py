from fastapi import FastAPI, HTTPException, status, Depends
from sqlalchemy import create_engine, Column, String, Integer, Numeric
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from pydantic import BaseModel, Field, field_validator
from typing import List
import os
from contextlib import asynccontextmanager

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


# Database Model
class VehicleDB(Base):
    __tablename__ = "vehicles"
    vin = Column(String(17), primary_key=True)
    manufacturer_name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    horse_power = Column(Integer, nullable=False)
    model_name = Column(String, nullable=False)
    model_year = Column(Integer, nullable=False)
    purchase_price = Column(Numeric(10, 2), nullable=False)
    fuel_type = Column(String, nullable=False)


# Pydantic Models
class VehicleBase(BaseModel):
    vin: str = Field(..., min_length=17, max_length=17)
    manufacturer_name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    horse_power: int = Field(..., gt=0)
    model_name: str = Field(..., min_length=1)
    model_year: int = Field(..., ge=1900, le=2025)
    purchase_price: float = Field(..., gt=0)
    fuel_type: str = Field(..., min_length=1)

    @field_validator("vin")
    def vin_must_be_alphanumeric(cls, v):
        if not v.isalnum():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid Vin",
            )
        return v.upper()

    @field_validator("fuel_type")
    def fuel_type_must_be_valid(cls, v):
        valid_types = ["gasoline", "diesel", "electric", "hybrid"]
        if v.lower() not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid fuel type",
            )
        return v.lower()


class VehicleUpdate(BaseModel):
    manufacturer_name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    horse_power: int = Field(..., gt=0)
    model_name: str = Field(..., min_length=1)
    model_year: int = Field(..., ge=1900, le=2025)
    purchase_price: float = Field(..., gt=0)
    fuel_type: str = Field(..., min_length=1)

    @field_validator("fuel_type")
    def fuel_type_must_be_valid(cls, v):
        valid_types = ["gasoline", "diesel", "electric", "hybrid"]
        if v.lower() not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid fuel type",
            )
        return v.lower()


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    Base.metadata.create_all(bind=engine)
    yield


# FastAPI app
app = FastAPI(title="Vehicle API", lifespan=lifespan)


# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Endpoints
@app.get("/vehicle", response_model=List[VehicleBase], status_code=status.HTTP_200_OK)
def get_all_vehicles(db: Session = Depends(get_db)):
    vehicles = db.query(VehicleDB).all()
    return vehicles


@app.post("/vehicle", response_model=VehicleBase, status_code=status.HTTP_201_CREATED)
def create_vehicle(vehicle: VehicleBase, db: Session = Depends(get_db)):
    existing = db.query(VehicleDB).filter(VehicleDB.vin.ilike(vehicle.vin)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Vin already exists",
        )

    db_vehicle = VehicleDB(**vehicle.model_dump())

    try:
        db.add(db_vehicle)
        db.commit()
        db.refresh(db_vehicle)
        return db_vehicle
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to create vehicle: {str(e)}",
        )


@app.get("/vehicle/{vin}", response_model=VehicleBase, status_code=status.HTTP_200_OK)
def get_vehicle(vin: str, db: Session = Depends(get_db)):
    vehicle = db.query(VehicleDB).filter(VehicleDB.vin.ilike(vin)).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Vin not found"
        )
    return vehicle


@app.put("/vehicle/{vin}", response_model=VehicleBase, status_code=status.HTTP_200_OK)
def update_vehicle(vin: str, vehicle: VehicleUpdate, db: Session = Depends(get_db)):
    db_vehicle = db.query(VehicleDB).filter(VehicleDB.vin.ilike(vin)).first()
    if not db_vehicle:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Vin not found"
        )

    db_vehicle.manufacturer_name = vehicle.manufacturer_name
    db_vehicle.description = vehicle.description
    db_vehicle.horse_power = vehicle.horse_power
    db_vehicle.model_name = vehicle.model_name
    db_vehicle.model_year = vehicle.model_year
    db_vehicle.purchase_price = vehicle.purchase_price
    db_vehicle.fuel_type = vehicle.fuel_type

    try:
        db.commit()
        db.refresh(db_vehicle)
        return db_vehicle
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to update vehicle: {str(e)}",
        )


@app.delete("/vehicle/{vin}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vin: str, db: Session = Depends(get_db)):
    vehicle = db.query(VehicleDB).filter(VehicleDB.vin.ilike(vin)).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Vin not found"
        )
    db.delete(vehicle)
    db.commit()
    return None


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Vehicle API",
        "docs": "/docs",
        "endpoints": [
            "GET /vehicle - Get all vehicles",
            "POST /vehicle - Create a vehicle",
            "GET /vehicle/{vin} - Get a vehicle",
            "PUT /vehicle/{vin} - Update a vehicle",
            "DELETE /vehicle/{vin} - Delete a vehicle",
        ],
    }
