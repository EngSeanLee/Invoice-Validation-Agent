"""Synthetic vendor profiles used to seed the anomaly baseline.

These are entirely made up (no real vendor, no real spend) -- clearly labeled
`Source=Synthetic` wherever they land, per the spec's cold-start note. They
exist purely so amount_above_vendor_avg / category_trend have something
realistic to compare against on the very first real invoice.
"""

from dataclasses import dataclass


@dataclass
class VendorProfile:
    vendor_name: str
    category: str
    line_item_description: str
    mean_amount: float
    stdev_fraction: float  # stdev as a fraction of mean_amount
    invoice_count: int
    invoice_code: str  # short code used to build invoice numbers


VENDOR_PROFILES: list[VendorProfile] = [
    VendorProfile("CloudStack Systems", "Software", "Monthly cloud hosting subscription", 1200.00, 0.10, 9, "CSS"),
    VendorProfile("DevTools Inc", "Software", "Developer tooling license (annual seats)", 450.00, 0.15, 7, "DTI"),
    VendorProfile("Office Depot Plus", "Office Supplies", "Office supplies restock", 220.00, 0.25, 10, "ODP"),
    VendorProfile("QuickSupply Co", "Office Supplies", "Printer paper and consumables", 95.00, 0.20, 8, "QSC"),
    VendorProfile("SkyLine Airways", "Travel", "Business travel airfare", 480.00, 0.30, 6, "SKY"),
    VendorProfile("CityStay Hotels", "Travel", "Business travel lodging", 340.00, 0.20, 6, "CTH"),
    VendorProfile("Metro Power & Light", "Utilities", "Monthly electricity service", 610.00, 0.08, 9, "MPL"),
    VendorProfile("Clearwave Internet", "Utilities", "Monthly internet/data service", 180.00, 0.05, 9, "CWI"),
    VendorProfile("Halden & Cole Consulting", "Professional Services", "Advisory retainer", 2400.00, 0.18, 5, "HCC"),
    VendorProfile("PixelForge Creative", "Marketing", "Brand/design services", 1350.00, 0.22, 6, "PFC"),
]
