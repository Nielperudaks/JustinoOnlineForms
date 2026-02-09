import uuid
from datetime import datetime, timezone, timedelta
from utils.helpers import hash_password
import logging
import random

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# DEPARTMENTS
# ─────────────────────────────────────────────

DEPARTMENTS = [
    {"name": "General", "code": "GEN", "description": "General office supplies, equipment, and administrative requests"},
    {"name": "Service", "code": "SVC", "description": "Motorpool, unit replacements, parts, and service center operations"},
    {"name": "Marketing", "code": "MKT", "description": "Marketing campaigns, sponsorships, events, and promotions"},
    {"name": "CIEG/TCG Sales", "code": "CIEG", "description": "Sales demos, showings, evaluations, and customer orders"},
    {"name": "Davao Service Center", "code": "DSC", "description": "Davao branch service operations and inventory"},
    {"name": "MCG", "code": "MCG", "description": "MCG item replacements, events, and technician requests"},
    {"name": "Accounting", "code": "ACCT", "description": "Barcode stickers and accounting operations"},
    {"name": "Purchasing", "code": "PUR", "description": "Special discounts, samples, demos, and procurement"},
    {"name": "HR and Admin", "code": "HR", "description": "Manpower, leave, benefits, and employee services"},
    {"name": "Warehouse", "code": "WHSE", "description": "Warehouse stock requests, warranty cards, and manuals"},
]

# ─────────────────────────────────────────────
# FORM TEMPLATES
# ─────────────────────────────────────────────

FORM_TEMPLATES = {
    "GEN": [
        {"name": "Office Supplies and Consumables", "fields": [
            {"name": "item_description", "label": "Item Description", "type": "textarea", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "text", "required": True},
            {"name": "date_needed", "label": "Date Needed", "type": "date", "required": True}
        ]},
        {"name": "Office Equipment", "fields": [
            {"name": "equipment_type", "label": "Equipment Type", "type": "select", "required": True, "options": ["Computer", "Printer", "Monitor", "Keyboard/Mouse", "Other"]},
            {"name": "specifications", "label": "Specifications", "type": "textarea", "required": True},
            {"name": "justification", "label": "Justification", "type": "textarea", "required": True}
        ]},
        {"name": "Borrowing of JC Vehicles", "fields": [
            {"name": "vehicle_type", "label": "Vehicle Type", "type": "text", "required": True},
            {"name": "destination", "label": "Destination", "type": "text", "required": True},
            {"name": "date_from", "label": "Date From", "type": "date", "required": True},
            {"name": "date_to", "label": "Date To", "type": "date", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}
        ]},
        {"name": "Marketing Collaterals - Merchandise", "fields": [
            {"name": "item_type", "label": "Item Type", "type": "select", "required": True, "options": ["T-shirt MaxSell", "T-shirt Shinsetsu", "T-shirt Kobewel", "T-shirt Diager", "Umbrella", "Foldable Fan", "Cap", "Planner", "Ballpen"]},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}
        ]},
        {"name": "Marketing Collaterals - Printed Materials", "fields": [
            {"name": "material_type", "label": "Material Type", "type": "select", "required": True, "options": ["Brochure", "Catalog", "Pricelist", "Poster", "Flyer", "Product Guide"]},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "brand", "label": "Brand", "type": "text", "required": False}
        ]},
        {"name": "Sales Support Materials", "fields": [
            {"name": "material_type", "label": "Material Type", "type": "select", "required": True, "options": ["Tarpaulin", "Roll-up Banner", "Wobbler", "Standee", "Display Visual"]},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "specifications", "label": "Specifications/Size", "type": "textarea", "required": True}
        ]},
        {"name": "Request for Company Representation", "fields": [
            {"name": "event_name", "label": "Event Name", "type": "text", "required": True},
            {"name": "date", "label": "Date", "type": "date", "required": True},
            {"name": "location", "label": "Location", "type": "text", "required": True},
            {"name": "budget", "label": "Estimated Budget", "type": "number", "required": True},
            {"name": "details", "label": "Details", "type": "textarea", "required": True}
        ]},
        {"name": "Liquidation", "fields": [
            {"name": "reference_number", "label": "Reference Number", "type": "text", "required": True},
            {"name": "amount", "label": "Amount", "type": "number", "required": True},
            {"name": "description", "label": "Description", "type": "textarea", "required": True},
            {"name": "receipts_attached", "label": "Receipts Attached", "type": "select", "required": True, "options": ["Yes", "No"]}
        ]},
        {"name": "Cash Float", "fields": [
            {"name": "amount", "label": "Amount Requested", "type": "number", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True},
            {"name": "date_needed", "label": "Date Needed", "type": "date", "required": True}
        ]},
        {"name": "Vehicle Parts and Maintenance", "fields": [
            {"name": "vehicle", "label": "Vehicle", "type": "text", "required": True},
            {"name": "parts_needed", "label": "Parts Needed", "type": "textarea", "required": True},
            {"name": "estimated_cost", "label": "Estimated Cost", "type": "number", "required": False}
        ]},
        {"name": "Product Information Request", "fields": [
            {"name": "product", "label": "Product", "type": "text", "required": True},
            {"name": "info_needed", "label": "Information Needed", "type": "textarea", "required": True}
        ]},
        {"name": "Content / Social Media Post Request", "fields": [
            {"name": "platform", "label": "Platform", "type": "select", "required": True, "options": ["Facebook", "Instagram", "LinkedIn", "TikTok", "Website"]},
            {"name": "content_type", "label": "Content Type", "type": "select", "required": True, "options": ["Post", "Story", "Reel", "Article"]},
            {"name": "description", "label": "Description", "type": "textarea", "required": True},
            {"name": "target_date", "label": "Target Post Date", "type": "date", "required": True}
        ]},
        {"name": "Photo / Video Coverage", "fields": [
            {"name": "event_name", "label": "Event Name", "type": "text", "required": True},
            {"name": "date", "label": "Date", "type": "date", "required": True},
            {"name": "location", "label": "Location", "type": "text", "required": True},
            {"name": "coverage_type", "label": "Coverage Type", "type": "select", "required": True, "options": ["Photo", "Video", "Both"]}
        ]},
        {"name": "Design & Printing Support - Employee ID", "fields": [
            {"name": "employee_name", "label": "Employee Name", "type": "text", "required": True},
            {"name": "department", "label": "Department", "type": "text", "required": True},
            {"name": "reason", "label": "Reason", "type": "select", "required": True, "options": ["New Hire", "Replacement", "Update"]}
        ]},
        {"name": "Item for Customer Demo", "fields": [
            {"name": "item", "label": "Item/Product", "type": "text", "required": True},
            {"name": "customer", "label": "Customer Name", "type": "text", "required": True},
            {"name": "demo_date", "label": "Demo Date", "type": "date", "required": True},
            {"name": "return_date", "label": "Expected Return Date", "type": "date", "required": True}
        ]},
        {"name": "Loaner Tools/Service Units", "fields": [
            {"name": "tool_description", "label": "Tool/Unit Description", "type": "textarea", "required": True},
            {"name": "borrower", "label": "Borrower Name", "type": "text", "required": True},
            {"name": "date_from", "label": "Borrow Date", "type": "date", "required": True},
            {"name": "date_to", "label": "Return Date", "type": "date", "required": True}
        ]},
        {"name": "Local Buy Out / Purchasing", "fields": [
            {"name": "item_description", "label": "Item Description", "type": "textarea", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "estimated_cost", "label": "Estimated Cost", "type": "number", "required": True},
            {"name": "supplier", "label": "Supplier", "type": "text", "required": False}
        ]},
        {"name": "Pull Out", "fields": [
            {"name": "item_description", "label": "Item Description", "type": "textarea", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "location_from", "label": "Pull Out From", "type": "text", "required": True},
            {"name": "reason", "label": "Reason", "type": "textarea", "required": True}
        ]},
    ],
    "SVC": [
        {"name": "Motorpool Parts Request", "fields": [
            {"name": "vehicle", "label": "Vehicle", "type": "text", "required": True},
            {"name": "parts", "label": "Parts Needed", "type": "textarea", "required": True},
            {"name": "urgency", "label": "Urgency", "type": "select", "required": True, "options": ["Low", "Normal", "High", "Critical"]}
        ]},
        {"name": "Unit Replacement (Defective)", "fields": [
            {"name": "unit_model", "label": "Unit Model", "type": "text", "required": True},
            {"name": "serial_number", "label": "Serial Number", "type": "text", "required": True},
            {"name": "defect_description", "label": "Defect Description", "type": "textarea", "required": True},
            {"name": "customer", "label": "Customer", "type": "text", "required": True}
        ]},
        {"name": "Parts Replacement (Defective)", "fields": [
            {"name": "part_name", "label": "Part Name", "type": "text", "required": True},
            {"name": "part_number", "label": "Part Number", "type": "text", "required": False},
            {"name": "defect_description", "label": "Defect Description", "type": "textarea", "required": True}
        ]},
        {"name": "Brand New Unit to Demo Unit", "fields": [
            {"name": "unit_model", "label": "Unit Model", "type": "text", "required": True},
            {"name": "serial_number", "label": "Serial Number", "type": "text", "required": True},
            {"name": "reason", "label": "Reason", "type": "textarea", "required": True}
        ]},
        {"name": "BGC Personal Requests", "fields": [
            {"name": "request_type", "label": "Request Type", "type": "text", "required": True},
            {"name": "details", "label": "Details", "type": "textarea", "required": True}
        ]},
        {"name": "Construction Materials Requests", "fields": [
            {"name": "materials", "label": "Materials Needed", "type": "textarea", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "text", "required": True},
            {"name": "project", "label": "Project/Location", "type": "text", "required": True}
        ]},
        {"name": "Credit and Collection", "fields": [
            {"name": "customer", "label": "Customer Name", "type": "text", "required": True},
            {"name": "amount", "label": "Amount", "type": "number", "required": True},
            {"name": "details", "label": "Details", "type": "textarea", "required": True}
        ]},
        {"name": "Collection Receipt & Provisional Receipt", "fields": [
            {"name": "receipt_type", "label": "Receipt Type", "type": "select", "required": True, "options": ["Collection Receipt", "Provisional Receipt"]},
            {"name": "customer", "label": "Customer", "type": "text", "required": True},
            {"name": "amount", "label": "Amount", "type": "number", "required": True},
            {"name": "reference", "label": "Reference Number", "type": "text", "required": False}
        ]},
    ],
    "MKT": [
        {"name": "Special Projects / Key Account Support", "fields": [
            {"name": "project_type", "label": "Project Type", "type": "select", "required": True, "options": ["Signage", "Tent", "Store Decoration", "Other"]},
            {"name": "account", "label": "Key Account", "type": "text", "required": True},
            {"name": "details", "label": "Details", "type": "textarea", "required": True},
            {"name": "budget", "label": "Estimated Budget", "type": "number", "required": True}
        ]},
        {"name": "Billboard / Endcap Replacement", "fields": [
            {"name": "location", "label": "Location", "type": "text", "required": True},
            {"name": "current_material", "label": "Current Material", "type": "text", "required": False},
            {"name": "new_design", "label": "New Design Description", "type": "textarea", "required": True}
        ]},
        {"name": "Online Store Boost Funding", "fields": [
            {"name": "platform", "label": "Platform", "type": "select", "required": True, "options": ["Shopee", "Lazada", "TikTok Shop", "Website", "Other"]},
            {"name": "budget", "label": "Budget Requested", "type": "number", "required": True},
            {"name": "duration", "label": "Duration (days)", "type": "number", "required": True},
            {"name": "objective", "label": "Objective", "type": "textarea", "required": True}
        ]},
        {"name": "Sponsorship / Solicitation Request", "fields": [
            {"name": "event_name", "label": "Event Name", "type": "text", "required": True},
            {"name": "organizer", "label": "Organizer", "type": "text", "required": True},
            {"name": "amount", "label": "Amount Requested", "type": "number", "required": True},
            {"name": "benefits", "label": "Benefits/ROI", "type": "textarea", "required": True}
        ]},
        {"name": "Event Support Request", "fields": [
            {"name": "event_name", "label": "Event Name", "type": "text", "required": True},
            {"name": "date", "label": "Event Date", "type": "date", "required": True},
            {"name": "support_needed", "label": "Support Needed", "type": "textarea", "required": True},
            {"name": "budget", "label": "Budget", "type": "number", "required": True}
        ]},
        {"name": "Product Information Request", "fields": [
            {"name": "product", "label": "Product", "type": "text", "required": True},
            {"name": "info_needed", "label": "Information Needed", "type": "textarea", "required": True}
        ]},
        {"name": "Budget Request for Marketing Activities", "fields": [
            {"name": "activity", "label": "Activity Description", "type": "textarea", "required": True},
            {"name": "budget", "label": "Budget Requested", "type": "number", "required": True},
            {"name": "timeline", "label": "Timeline", "type": "text", "required": True},
            {"name": "expected_roi", "label": "Expected ROI", "type": "textarea", "required": False}
        ]},
    ],
    "CIEG": [
        {"name": "Demo Unit", "fields": [{"name": "unit_model", "label": "Unit Model", "type": "text", "required": True}, {"name": "customer", "label": "Customer", "type": "text", "required": True}, {"name": "demo_date", "label": "Demo Date", "type": "date", "required": True}, {"name": "location", "label": "Location", "type": "text", "required": True}]},
        {"name": "Brand New to Demo", "fields": [{"name": "unit_model", "label": "Unit Model", "type": "text", "required": True}, {"name": "serial_number", "label": "Serial Number", "type": "text", "required": True}, {"name": "reason", "label": "Reason", "type": "textarea", "required": True}]},
        {"name": "Showing", "fields": [{"name": "product", "label": "Product", "type": "text", "required": True}, {"name": "customer", "label": "Customer", "type": "text", "required": True}, {"name": "date", "label": "Date", "type": "date", "required": True}]},
        {"name": "Sample for Evaluation", "fields": [{"name": "product", "label": "Product", "type": "text", "required": True}, {"name": "customer", "label": "Customer", "type": "text", "required": True}, {"name": "evaluation_period", "label": "Evaluation Period (days)", "type": "number", "required": True}]},
        {"name": "Loaner Tool", "fields": [{"name": "tool", "label": "Tool Description", "type": "text", "required": True}, {"name": "borrower", "label": "Borrower", "type": "text", "required": True}, {"name": "date_from", "label": "From", "type": "date", "required": True}, {"name": "date_to", "label": "To", "type": "date", "required": True}]},
        {"name": "Pull Out", "fields": [{"name": "item", "label": "Item", "type": "text", "required": True}, {"name": "location", "label": "From Location", "type": "text", "required": True}, {"name": "reason", "label": "Reason", "type": "textarea", "required": True}]},
        {"name": "Request for Technician (Demo)", "fields": [{"name": "product", "label": "Product", "type": "text", "required": True}, {"name": "customer", "label": "Customer", "type": "text", "required": True}, {"name": "date", "label": "Date Needed", "type": "date", "required": True}, {"name": "location", "label": "Location", "type": "text", "required": True}]},
        {"name": "Repair at Site", "fields": [{"name": "unit_model", "label": "Unit Model", "type": "text", "required": True}, {"name": "issue", "label": "Issue Description", "type": "textarea", "required": True}, {"name": "customer", "label": "Customer", "type": "text", "required": True}, {"name": "site_address", "label": "Site Address", "type": "text", "required": True}]},
        {"name": "Item for Replacement", "fields": [{"name": "item", "label": "Item", "type": "text", "required": True}, {"name": "reason", "label": "Reason for Replacement", "type": "textarea", "required": True}, {"name": "customer", "label": "Customer", "type": "text", "required": True}]},
        {"name": "FOC", "fields": [{"name": "item", "label": "Item", "type": "text", "required": True}, {"name": "customer", "label": "Customer", "type": "text", "required": True}, {"name": "reason", "label": "Reason", "type": "textarea", "required": True}]},
        {"name": "Manual Entry", "fields": [{"name": "entry_type", "label": "Entry Type", "type": "text", "required": True}, {"name": "details", "label": "Details", "type": "textarea", "required": True}]},
        {"name": "Price Approval Form", "fields": [{"name": "product", "label": "Product", "type": "text", "required": True}, {"name": "standard_price", "label": "Standard Price", "type": "number", "required": True}, {"name": "requested_price", "label": "Requested Price", "type": "number", "required": True}, {"name": "customer", "label": "Customer", "type": "text", "required": True}, {"name": "justification", "label": "Justification", "type": "textarea", "required": True}]},
        {"name": "Cash Float", "fields": [{"name": "amount", "label": "Amount", "type": "number", "required": True}, {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}]},
        {"name": "Customer Order (PO/Check to Follow)", "fields": [{"name": "customer", "label": "Customer", "type": "text", "required": True}, {"name": "items", "label": "Items Ordered", "type": "textarea", "required": True}, {"name": "total_amount", "label": "Total Amount", "type": "number", "required": True}, {"name": "payment_terms", "label": "Payment Terms", "type": "text", "required": True}]},
        {"name": "Advance Stocking (TRQ)", "fields": [{"name": "items", "label": "Items", "type": "textarea", "required": True}, {"name": "quantity", "label": "Quantity", "type": "number", "required": True}, {"name": "reason", "label": "Reason", "type": "textarea", "required": True}]},
    ],
    "DSC": [
        {"name": "Cash Float - Budget For Billable PMS", "fields": [{"name": "amount", "label": "Amount", "type": "number", "required": True}, {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}]},
        {"name": "Re-Ordering Of Stock - Unit & Accessories", "fields": [{"name": "items", "label": "Items", "type": "textarea", "required": True}, {"name": "quantity", "label": "Quantity", "type": "text", "required": True}, {"name": "current_stock", "label": "Current Stock Level", "type": "text", "required": False}]},
        {"name": "Re-Ordering Of Spareparts - Repairs", "fields": [{"name": "parts", "label": "Spare Parts Needed", "type": "textarea", "required": True}, {"name": "quantity", "label": "Quantity", "type": "text", "required": True}]},
        {"name": "Provisional & Collection Receipts", "fields": [{"name": "receipt_type", "label": "Receipt Type", "type": "select", "required": True, "options": ["Provisional", "Collection"]}, {"name": "customer", "label": "Customer", "type": "text", "required": True}, {"name": "amount", "label": "Amount", "type": "number", "required": True}]},
        {"name": "Delivery Receipts & Cash Invoice", "fields": [{"name": "customer", "label": "Customer", "type": "text", "required": True}, {"name": "items", "label": "Items", "type": "textarea", "required": True}, {"name": "amount", "label": "Amount", "type": "number", "required": True}]},
        {"name": "Store Use - Consumables & Non Consumables", "fields": [{"name": "item_type", "label": "Type", "type": "select", "required": True, "options": ["Consumable", "Non-Consumable"]}, {"name": "items", "label": "Items", "type": "textarea", "required": True}, {"name": "quantity", "label": "Quantity", "type": "text", "required": True}]},
    ],
    "MCG": [
        {"name": "Item Replacement", "fields": [{"name": "item", "label": "Item", "type": "text", "required": True}, {"name": "reason", "label": "Reason", "type": "textarea", "required": True}, {"name": "outlet", "label": "Outlet", "type": "text", "required": True}]},
        {"name": "Item Use for Event (Caravan)", "fields": [{"name": "items", "label": "Items Needed", "type": "textarea", "required": True}, {"name": "event", "label": "Event Name", "type": "text", "required": True}, {"name": "date", "label": "Event Date", "type": "date", "required": True}]},
        {"name": "Technician Request", "fields": [{"name": "issue", "label": "Issue Description", "type": "textarea", "required": True}, {"name": "location", "label": "Location", "type": "text", "required": True}, {"name": "date_needed", "label": "Date Needed", "type": "date", "required": True}]},
    ],
    "ACCT": [
        {"name": "Barcode Stickers for MCG Outlets", "fields": [{"name": "outlet", "label": "Outlet", "type": "text", "required": True}, {"name": "quantity", "label": "Quantity", "type": "number", "required": True}, {"name": "product_list", "label": "Product List", "type": "textarea", "required": True}]},
    ],
    "PUR": [
        {"name": "Special Discount", "fields": [{"name": "product", "label": "Product", "type": "text", "required": True}, {"name": "standard_price", "label": "Standard Price", "type": "number", "required": True}, {"name": "requested_discount", "label": "Requested Discount %", "type": "number", "required": True}, {"name": "reason", "label": "Reason", "type": "textarea", "required": True}]},
        {"name": "Product Sample / Own Use", "fields": [{"name": "product", "label": "Product", "type": "text", "required": True}, {"name": "quantity", "label": "Quantity", "type": "number", "required": True}, {"name": "purpose", "label": "Purpose", "type": "select", "required": True, "options": ["Sample", "Own Use"]}]},
        {"name": "Product Demo", "fields": [{"name": "product", "label": "Product", "type": "text", "required": True}, {"name": "customer", "label": "Customer", "type": "text", "required": True}, {"name": "demo_date", "label": "Demo Date", "type": "date", "required": True}]},
        {"name": "Local Buy Out", "fields": [{"name": "item", "label": "Item Description", "type": "textarea", "required": True}, {"name": "quantity", "label": "Quantity", "type": "number", "required": True}, {"name": "estimated_cost", "label": "Estimated Cost", "type": "number", "required": True}, {"name": "supplier", "label": "Preferred Supplier", "type": "text", "required": False}]},
        {"name": "Representation", "fields": [{"name": "event", "label": "Event/Meeting", "type": "text", "required": True}, {"name": "date", "label": "Date", "type": "date", "required": True}, {"name": "budget", "label": "Budget", "type": "number", "required": True}, {"name": "details", "label": "Details", "type": "textarea", "required": True}]},
        {"name": "Loaner Tools", "fields": [{"name": "tool", "label": "Tool", "type": "text", "required": True}, {"name": "borrower", "label": "Borrower", "type": "text", "required": True}, {"name": "duration", "label": "Duration (days)", "type": "number", "required": True}]},
        {"name": "QC Reworks", "fields": [{"name": "product", "label": "Product", "type": "text", "required": True}, {"name": "issue", "label": "QC Issue", "type": "textarea", "required": True}, {"name": "quantity_affected", "label": "Quantity Affected", "type": "number", "required": True}]},
    ],
    "HR": [
        {"name": "Manpower Request", "fields": [{"name": "position", "label": "Position", "type": "text", "required": True}, {"name": "department", "label": "Department", "type": "text", "required": True}, {"name": "headcount", "label": "Headcount", "type": "number", "required": True}, {"name": "justification", "label": "Justification", "type": "textarea", "required": True}]},
        {"name": "Leave Request", "fields": [{"name": "leave_type", "label": "Leave Type", "type": "select", "required": True, "options": ["Vacation", "Sick", "Emergency", "Maternity/Paternity", "Other"]}, {"name": "date_from", "label": "Date From", "type": "date", "required": True}, {"name": "date_to", "label": "Date To", "type": "date", "required": True}, {"name": "reason", "label": "Reason", "type": "textarea", "required": True}]},
        {"name": "Cash Advance Request", "fields": [{"name": "amount", "label": "Amount", "type": "number", "required": True}, {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}, {"name": "repayment_terms", "label": "Repayment Terms", "type": "text", "required": True}]},
        {"name": "Bank Loan Request", "fields": [{"name": "bank", "label": "Bank", "type": "text", "required": True}, {"name": "amount", "label": "Amount", "type": "number", "required": True}, {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}]},
        {"name": "Health Benefit Reimbursement", "fields": [{"name": "claim_type", "label": "Claim Type", "type": "select", "required": True, "options": ["Medical", "Dental", "Vision", "Other"]}, {"name": "amount", "label": "Amount", "type": "number", "required": True}, {"name": "date_of_service", "label": "Date of Service", "type": "date", "required": True}, {"name": "details", "label": "Details", "type": "textarea", "required": True}]},
        {"name": "Flight Request (Official Travel)", "fields": [{"name": "destination", "label": "Destination", "type": "text", "required": True}, {"name": "date_departure", "label": "Departure Date", "type": "date", "required": True}, {"name": "date_return", "label": "Return Date", "type": "date", "required": True}, {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}]},
        {"name": "Educational Assistance Request", "fields": [{"name": "school", "label": "School/Institution", "type": "text", "required": True}, {"name": "course", "label": "Course/Program", "type": "text", "required": True}, {"name": "amount", "label": "Amount Requested", "type": "number", "required": True}]},
        {"name": "COE Request", "fields": [{"name": "purpose", "label": "Purpose", "type": "select", "required": True, "options": ["Bank Requirement", "Visa Application", "Government", "Other"]}, {"name": "details", "label": "Additional Details", "type": "textarea", "required": False}]},
        {"name": "Pay Slip Request", "fields": [{"name": "period", "label": "Pay Period", "type": "text", "required": True}, {"name": "purpose", "label": "Purpose", "type": "text", "required": True}]},
        {"name": "Office Supplies Request", "fields": [{"name": "items", "label": "Items Needed", "type": "textarea", "required": True}, {"name": "quantity", "label": "Quantity", "type": "text", "required": True}]},
        {"name": "Equipment Supplies Request", "fields": [{"name": "equipment", "label": "Equipment", "type": "text", "required": True}, {"name": "specifications", "label": "Specifications", "type": "textarea", "required": True}]},
        {"name": "Uniform Request", "fields": [{"name": "size", "label": "Size", "type": "select", "required": True, "options": ["XS", "S", "M", "L", "XL", "XXL"]}, {"name": "quantity", "label": "Quantity", "type": "number", "required": True}, {"name": "type", "label": "Uniform Type", "type": "text", "required": True}]},
        {"name": "Employee ID / Lanyard Issuance", "fields": [{"name": "type", "label": "Type", "type": "select", "required": True, "options": ["New ID", "Replacement ID", "Lanyard"]}, {"name": "reason", "label": "Reason", "type": "text", "required": True}]},
        {"name": "Purchase Order Form", "fields": [{"name": "vendor", "label": "Vendor", "type": "text", "required": True}, {"name": "items", "label": "Items", "type": "textarea", "required": True}, {"name": "total_amount", "label": "Total Amount", "type": "number", "required": True}]},
        {"name": "Cash Float Slip Form (Petty Cash)", "fields": [{"name": "amount", "label": "Amount", "type": "number", "required": True}, {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}]},
        {"name": "Gate Pass Form", "fields": [{"name": "items", "label": "Items to Pass", "type": "textarea", "required": True}, {"name": "destination", "label": "Destination", "type": "text", "required": True}, {"name": "date", "label": "Date", "type": "date", "required": True}]},
        {"name": "Vehicle Request", "fields": [{"name": "destination", "label": "Destination", "type": "text", "required": True}, {"name": "date", "label": "Date", "type": "date", "required": True}, {"name": "passengers", "label": "Number of Passengers", "type": "number", "required": True}, {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}]},
    ],
    "WHSE": [
        {"name": "Own Used (QC/WHSE/LOG)", "fields": [{"name": "item", "label": "Item", "type": "text", "required": True}, {"name": "quantity", "label": "Quantity", "type": "number", "required": True}, {"name": "department", "label": "Department", "type": "select", "required": True, "options": ["QC", "Warehouse", "Logistics"]}]},
        {"name": "Cash Float", "fields": [{"name": "amount", "label": "Amount", "type": "number", "required": True}, {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}]},
        {"name": "Local Buy Out (Box/Tape/Etc)", "fields": [{"name": "item", "label": "Item", "type": "text", "required": True}, {"name": "quantity", "label": "Quantity", "type": "number", "required": True}, {"name": "estimated_cost", "label": "Estimated Cost", "type": "number", "required": True}]},
        {"name": "Request for Sticker (Powertools/LCE/Etc)", "fields": [{"name": "product_line", "label": "Product Line", "type": "select", "required": True, "options": ["Powertools", "LCE", "Other"]}, {"name": "quantity", "label": "Quantity", "type": "number", "required": True}, {"name": "details", "label": "Details", "type": "textarea", "required": False}]},
        {"name": "Request for Warranty Card (Powertools/LCE/Etc)", "fields": [{"name": "product_line", "label": "Product Line", "type": "select", "required": True, "options": ["Powertools", "LCE", "Other"]}, {"name": "quantity", "label": "Quantity", "type": "number", "required": True}]},
        {"name": "Request for Manual (Powertools/LCE/Etc)", "fields": [{"name": "product_line", "label": "Product Line", "type": "select", "required": True, "options": ["Powertools", "LCE", "Other"]}, {"name": "quantity", "label": "Quantity", "type": "number", "required": True}]},
        {"name": "Request for Manual DR (Completion)", "fields": [{"name": "dr_number", "label": "DR Number", "type": "text", "required": True}, {"name": "details", "label": "Details", "type": "textarea", "required": True}]},
    ],
}

# ─────────────────────────────────────────────
# SEED USERS (per department)
# ─────────────────────────────────────────────
# Each user: (email, password, name, role, dept_code)
SEED_USERS = [
    # Super Admin
    ("admin@company.com", "admin123", "Super Admin", "super_admin", "GEN"),
    # General
    ("maria.santos@company.com", "pass123", "Maria Santos", "approver", "GEN"),
    ("ricardo.cruz@company.com", "pass123", "Ricardo Cruz", "approver", "GEN"),
    ("ana.reyes@company.com", "pass123", "Ana Reyes", "requestor", "GEN"),
    ("carlos.mendoza@company.com", "pass123", "Carlos Mendoza", "both", "GEN"),
    # Service
    ("pedro.villanueva@company.com", "pass123", "Pedro Villanueva", "approver", "SVC"),
    ("elena.garcia@company.com", "pass123", "Elena Garcia", "both", "SVC"),
    ("jose.santos@company.com", "pass123", "Jose Santos", "requestor", "SVC"),
    # Marketing
    ("sofia.martinez@company.com", "pass123", "Sofia Martinez", "approver", "MKT"),
    ("diego.torres@company.com", "pass123", "Diego Torres", "requestor", "MKT"),
    ("lisa.fernandez@company.com", "pass123", "Lisa Fernandez", "both", "MKT"),
    # CIEG/TCG Sales
    ("roberto.lim@company.com", "pass123", "Roberto Lim", "approver", "CIEG"),
    ("patricia.tan@company.com", "pass123", "Patricia Tan", "both", "CIEG"),
    ("mark.villanueva@company.com", "pass123", "Mark Villanueva", "requestor", "CIEG"),
    # Davao Service Center
    ("miguel.aquino@company.com", "pass123", "Miguel Aquino", "approver", "DSC"),
    ("rosa.flores@company.com", "pass123", "Rosa Flores", "requestor", "DSC"),
    # MCG
    ("antonio.ramos@company.com", "pass123", "Antonio Ramos", "approver", "MCG"),
    ("jenny.ocampo@company.com", "pass123", "Jenny Ocampo", "requestor", "MCG"),
    # Accounting
    ("carmen.delacruz@company.com", "pass123", "Carmen Dela Cruz", "approver", "ACCT"),
    ("ralph.navarro@company.com", "pass123", "Ralph Navarro", "requestor", "ACCT"),
    # Purchasing
    ("francisco.bautista@company.com", "pass123", "Francisco Bautista", "approver", "PUR"),
    ("lucia.navarro@company.com", "pass123", "Lucia Navarro", "requestor", "PUR"),
    # HR and Admin
    ("teresa.gonzales@company.com", "pass123", "Teresa Gonzales", "approver", "HR"),
    ("manuel.reyes@company.com", "pass123", "Manuel Reyes", "both", "HR"),
    ("grace.lim@company.com", "pass123", "Grace Lim", "requestor", "HR"),
    # Warehouse
    ("jorge.santos@company.com", "pass123", "Jorge Santos", "approver", "WHSE"),
    ("isabel.cruz@company.com", "pass123", "Isabel Cruz", "requestor", "WHSE"),
]

# ─────────────────────────────────────────────
# APPROVER ASSIGNMENTS
# Maps: (dept_code, form_name) -> [(step, user_email), ...]
# ─────────────────────────────────────────────
APPROVER_ASSIGNMENTS = {
    ("GEN", "Office Supplies and Consumables"): [("maria.santos@company.com", 1), ("ricardo.cruz@company.com", 2)],
    ("GEN", "Office Equipment"): [("maria.santos@company.com", 1), ("ricardo.cruz@company.com", 2)],
    ("GEN", "Borrowing of JC Vehicles"): [("maria.santos@company.com", 1)],
    ("GEN", "Cash Float"): [("maria.santos@company.com", 1), ("ricardo.cruz@company.com", 2)],
    ("GEN", "Local Buy Out / Purchasing"): [("maria.santos@company.com", 1)],
    ("GEN", "Request for Company Representation"): [("maria.santos@company.com", 1), ("ricardo.cruz@company.com", 2)],
    ("GEN", "Liquidation"): [("maria.santos@company.com", 1)],
    ("GEN", "Pull Out"): [("maria.santos@company.com", 1)],
    ("GEN", "Marketing Collaterals - Merchandise"): [("maria.santos@company.com", 1)],
    ("GEN", "Content / Social Media Post Request"): [("maria.santos@company.com", 1)],
    ("SVC", "Motorpool Parts Request"): [("pedro.villanueva@company.com", 1)],
    ("SVC", "Unit Replacement (Defective)"): [("pedro.villanueva@company.com", 1)],
    ("SVC", "Parts Replacement (Defective)"): [("pedro.villanueva@company.com", 1)],
    ("SVC", "Credit and Collection"): [("pedro.villanueva@company.com", 1)],
    ("MKT", "Event Support Request"): [("sofia.martinez@company.com", 1)],
    ("MKT", "Budget Request for Marketing Activities"): [("sofia.martinez@company.com", 1)],
    ("MKT", "Sponsorship / Solicitation Request"): [("sofia.martinez@company.com", 1)],
    ("MKT", "Online Store Boost Funding"): [("sofia.martinez@company.com", 1)],
    ("CIEG", "Demo Unit"): [("roberto.lim@company.com", 1)],
    ("CIEG", "Price Approval Form"): [("roberto.lim@company.com", 1)],
    ("CIEG", "Customer Order (PO/Check to Follow)"): [("roberto.lim@company.com", 1)],
    ("CIEG", "Cash Float"): [("roberto.lim@company.com", 1)],
    ("DSC", "Cash Float - Budget For Billable PMS"): [("miguel.aquino@company.com", 1)],
    ("DSC", "Re-Ordering Of Stock - Unit & Accessories"): [("miguel.aquino@company.com", 1)],
    ("MCG", "Item Replacement"): [("antonio.ramos@company.com", 1)],
    ("MCG", "Technician Request"): [("antonio.ramos@company.com", 1)],
    ("ACCT", "Barcode Stickers for MCG Outlets"): [("carmen.delacruz@company.com", 1)],
    ("PUR", "Special Discount"): [("francisco.bautista@company.com", 1)],
    ("PUR", "Local Buy Out"): [("francisco.bautista@company.com", 1)],
    ("PUR", "QC Reworks"): [("francisco.bautista@company.com", 1)],
    ("HR", "Leave Request"): [("teresa.gonzales@company.com", 1)],
    ("HR", "Cash Advance Request"): [("teresa.gonzales@company.com", 1)],
    ("HR", "Manpower Request"): [("teresa.gonzales@company.com", 1)],
    ("HR", "Flight Request (Official Travel)"): [("teresa.gonzales@company.com", 1)],
    ("HR", "Uniform Request"): [("teresa.gonzales@company.com", 1)],
    ("HR", "Gate Pass Form"): [("teresa.gonzales@company.com", 1)],
    ("HR", "Vehicle Request"): [("teresa.gonzales@company.com", 1)],
    ("WHSE", "Own Used (QC/WHSE/LOG)"): [("jorge.santos@company.com", 1)],
    ("WHSE", "Cash Float"): [("jorge.santos@company.com", 1)],
    ("WHSE", "Local Buy Out (Box/Tape/Etc)"): [("jorge.santos@company.com", 1)],
}

# ─────────────────────────────────────────────
# SAMPLE REQUESTS
# (requester_email, dept_code, form_name, title, form_data, priority, status_override, days_ago)
# status_override: None = use normal flow, "approved", "rejected", "in_progress"
# ─────────────────────────────────────────────
SAMPLE_REQUESTS = [
    # GEN — Approved (both steps)
    ("ana.reyes@company.com", "GEN", "Office Supplies and Consumables", "Restock of printing paper and ink cartridges",
     {"item_description": "A4 Bond Paper (10 reams), HP 680 Black Ink (3 pcs), HP 680 Tri-color Ink (2 pcs)", "quantity": "15", "purpose": "Monthly office replenishment", "date_needed": "2026-02-15"},
     "normal", "approved", 7),

    ("carlos.mendoza@company.com", "GEN", "Office Equipment", "New laptop for marketing coordinator",
     {"equipment_type": "Computer", "specifications": "Intel i7 13th Gen, 16GB RAM, 512GB SSD, 14-inch display", "justification": "Current unit is 5 years old, frequent crashes during presentations"},
     "high", "approved", 12),

    # GEN — In progress (step 1 approved, step 2 pending)
    ("ana.reyes@company.com", "GEN", "Cash Float", "Cash float for client lunch meeting",
     {"amount": "5000", "purpose": "Client entertainment - ABC Construction meeting for Q1 project discussion", "date_needed": "2026-02-10"},
     "normal", "in_progress_step2", 3),

    # GEN — In progress (step 1 pending)
    ("carlos.mendoza@company.com", "GEN", "Request for Company Representation", "Annual Hardware Expo 2026 attendance",
     {"event_name": "Annual Hardware Expo 2026", "date": "2026-03-15", "location": "SMX Convention Center, Manila", "budget": "25000", "details": "3-day expo, need booth setup and promotional materials. Expected 500+ visitors per day."},
     "high", "in_progress", 1),

    # GEN — Rejected
    ("ana.reyes@company.com", "GEN", "Local Buy Out / Purchasing", "Purchase of standing desk converter",
     {"item_description": "Ergonomic standing desk converter with adjustable height", "quantity": "3", "estimated_cost": "15000", "supplier": "Ergonomic Solutions PH"},
     "low", "rejected", 10),

    # GEN — Approved (1 step only)
    ("carlos.mendoza@company.com", "GEN", "Marketing Collaterals - Merchandise", "T-shirts for product launch event",
     {"item_type": "T-shirt MaxSell", "quantity": "100", "purpose": "Product launch giveaway for MaxSell Power Drill series"},
     "urgent", "approved", 5),

    # SVC
    ("jose.santos@company.com", "SVC", "Motorpool Parts Request", "Brake pads replacement for delivery truck",
     {"vehicle": "Isuzu Elf NKR - Plate ABC-1234", "parts": "Front brake pads (set of 4), brake fluid DOT4 (2L)", "urgency": "High"},
     "high", "approved", 8),

    ("elena.garcia@company.com", "SVC", "Unit Replacement (Defective)", "Replace defective Makita drill for customer",
     {"unit_model": "Makita DHP486Z", "serial_number": "SN-2024-08-00451", "defect_description": "Motor overheating after 2 minutes of use. Under warranty period.", "customer": "Metro Hardware Corp"},
     "urgent", "in_progress", 2),

    # MKT
    ("diego.torres@company.com", "MKT", "Event Support Request", "Booth setup for SM Megamall Trade Fair",
     {"event_name": "SM Megamall Home & Tools Trade Fair", "date": "2026-03-01", "support_needed": "10x10 booth, product display shelves, LED TV for demo videos, standees (3 pcs), promotional flyers (500 pcs)", "budget": "45000"},
     "high", "approved", 14),

    ("lisa.fernandez@company.com", "MKT", "Online Store Boost Funding", "Shopee 3.3 sale campaign boost",
     {"platform": "Shopee", "budget": "30000", "duration": "7", "objective": "Increase visibility for MaxSell power tools during 3.3 mega sale. Target 200% increase in store visits."},
     "normal", "in_progress", 1),

    ("diego.torres@company.com", "MKT", "Budget Request for Marketing Activities", "Q2 social media ad campaign",
     {"activity": "Facebook and Instagram paid ads for Q2 product launches, including video production and influencer collaboration", "budget": "120000", "timeline": "April-June 2026", "expected_roi": "Expected 3x ROAS based on Q1 performance"},
     "normal", "in_progress", 2),

    # CIEG
    ("mark.villanueva@company.com", "CIEG", "Demo Unit", "Demo unit for ABC Construction bid",
     {"unit_model": "Kobewel MIG Welder 350A", "customer": "ABC Construction Corp", "demo_date": "2026-02-20", "location": "ABC Construction yard, Quezon City"},
     "high", "approved", 6),

    ("patricia.tan@company.com", "CIEG", "Price Approval Form", "Special pricing for bulk order - Metro Builders",
     {"product": "Diager SDS Plus Drill Bits (Full Range)", "standard_price": "85000", "requested_price": "72000", "customer": "Metro Builders Supply", "justification": "Bulk order of 50 sets. Long-term account with good payment history. Competitor offering at 70k."},
     "normal", "in_progress", 1),

    # DSC
    ("rosa.flores@company.com", "DSC", "Cash Float - Budget For Billable PMS", "PMS budget for February billable services",
     {"amount": "15000", "purpose": "Preventive maintenance service budget for 8 scheduled customer visits in Davao area"},
     "normal", "approved", 9),

    ("rosa.flores@company.com", "DSC", "Re-Ordering Of Stock - Unit & Accessories", "Restock welding accessories",
     {"items": "Welding electrode E6013 (50kg), Welding gloves (10 pairs), Auto-darkening helmets (3 pcs), Wire brush (10 pcs)", "quantity": "Various - see items", "current_stock": "Electrodes: 5kg, Gloves: 2 pairs, Helmets: 0, Wire brush: 1"},
     "normal", "in_progress", 3),

    # MCG
    ("jenny.ocampo@company.com", "MCG", "Item Replacement", "Replace damaged display unit at SM North outlet",
     {"item": "Shinsetsu Air Conditioner 1.5HP Window Type (Display Model)", "reason": "Display unit compressor failure. Unit no longer turns on. Need replacement for showroom display.", "outlet": "SM North EDSA - MCG Booth"},
     "high", "approved", 4),

    ("jenny.ocampo@company.com", "MCG", "Technician Request", "Technician needed for SM Megamall demo day",
     {"issue": "Need technician to demonstrate Shinsetsu split-type AC installation process during mall promo day", "location": "SM Megamall Ground Floor - MCG area", "date_needed": "2026-02-22"},
     "normal", "in_progress", 1),

    # ACCT
    ("ralph.navarro@company.com", "ACCT", "Barcode Stickers for MCG Outlets", "New barcode batch for Shinsetsu products",
     {"outlet": "All MCG outlets (SM North, SM Megamall, SM MOA, Robinsons Galleria)", "quantity": "2000", "product_list": "Shinsetsu Window AC 1HP, 1.5HP, 2HP; Split AC 1HP, 1.5HP, 2HP; Portable AC 1HP"},
     "normal", "approved", 11),

    # PUR
    ("lucia.navarro@company.com", "PUR", "Special Discount", "Bulk discount for JC Hardware chain order",
     {"product": "MaxSell Cordless Drill 20V Kit", "standard_price": "4500", "requested_discount": "15", "reason": "JC Hardware ordering 200 units for 15 branches. Annual contract renewal. Competitor matched at 18% discount."},
     "high", "in_progress", 2),

    ("lucia.navarro@company.com", "PUR", "Local Buy Out", "Emergency purchase of packaging materials",
     {"item": "Corrugated boxes 18x12x12 (200 pcs), Bubble wrap 12-inch roll (5 rolls), Packing tape 2-inch (20 rolls)", "quantity": "200", "estimated_cost": "12500", "supplier": "PhilPack Solutions Inc."},
     "normal", "approved", 6),

    # HR
    ("grace.lim@company.com", "HR", "Leave Request", "Vacation leave for family trip",
     {"leave_type": "Vacation", "date_from": "2026-03-10", "date_to": "2026-03-14", "reason": "Annual family vacation to Boracay. All pending tasks delegated to colleague."},
     "normal", "approved", 15),

    ("manuel.reyes@company.com", "HR", "Manpower Request", "Additional warehouse staff for peak season",
     {"position": "Warehouse Associate", "department": "Warehouse", "headcount": "3", "justification": "Upcoming peak season March-May. Current staff of 8 cannot handle projected 40% increase in daily orders."},
     "high", "in_progress", 4),

    ("grace.lim@company.com", "HR", "Cash Advance Request", "Cash advance for Davao training trip",
     {"amount": "8000", "purpose": "Travel allowance for 3-day product training in Davao Service Center. Covers meals and transportation.", "repayment_terms": "Deduct from next salary"},
     "normal", "approved", 8),

    ("grace.lim@company.com", "HR", "Flight Request (Official Travel)", "Flight to Davao for quarterly review",
     {"destination": "Davao City", "date_departure": "2026-03-05", "date_return": "2026-03-07", "purpose": "Quarterly performance review and product training at Davao Service Center"},
     "normal", "in_progress", 2),

    ("manuel.reyes@company.com", "HR", "Uniform Request", "New uniforms for warehouse team",
     {"size": "L", "quantity": "10", "type": "Warehouse polo shirt with company logo"},
     "low", "approved", 20),

    # WHSE
    ("isabel.cruz@company.com", "WHSE", "Own Used (QC/WHSE/LOG)", "Packaging tape for outbound shipments",
     {"item": "OPP Packing Tape 2-inch Clear", "quantity": "50", "department": "Logistics"},
     "normal", "approved", 5),

    ("isabel.cruz@company.com", "WHSE", "Local Buy Out (Box/Tape/Etc)", "Emergency box purchase for large order",
     {"item": "Corrugated shipping boxes 24x18x18", "quantity": "100", "estimated_cost": "8500"},
     "high", "in_progress", 1),

    ("isabel.cruz@company.com", "WHSE", "Cash Float", "Petty cash for warehouse supplies",
     {"amount": "3000", "purpose": "Small purchases: cleaning supplies, hand tools, marking pens for the warehouse"},
     "normal", "approved", 13),
]


# ─────────────────────────────────────────────
# SEED FUNCTION
# ─────────────────────────────────────────────

async def seed_data(db):
    """Seed departments, templates, users, approver chains, requests, and notifications."""
    existing = await db.departments.count_documents({})
    if existing > 0:
        logger.info("Data already seeded, skipping.")
        return

    logger.info("Seeding initial data...")
    now = datetime.now(timezone.utc)

    # ── 1. Departments ──
    dept_map = {}  # code -> id
    for d in DEPARTMENTS:
        doc = {
            "id": str(uuid.uuid4()), "name": d["name"], "code": d["code"],
            "description": d["description"], "is_active": True,
            "created_at": now.isoformat()
        }
        await db.departments.insert_one(doc)
        dept_map[d["code"]] = doc["id"]
    logger.info(f"  {len(dept_map)} departments created.")

    # ── 2. Form Templates ──
    tmpl_lookup = {}  # (dept_code, form_name) -> template doc (without _id)
    tmpl_count = 0
    for dept_code, forms in FORM_TEMPLATES.items():
        dept_id = dept_map.get(dept_code)
        if not dept_id:
            continue
        for f in forms:
            doc = {
                "id": str(uuid.uuid4()), "department_id": dept_id,
                "name": f["name"], "description": "",
                "fields": f["fields"], "approver_chain": [],
                "is_active": True, "created_at": now.isoformat()
            }
            await db.form_templates.insert_one(doc)
            tmpl_lookup[(dept_code, f["name"])] = {k: v for k, v in doc.items() if k != "_id"}
            tmpl_count += 1
    logger.info(f"  {tmpl_count} form templates created.")

    # ── 3. Users ──
    user_map = {}  # email -> user doc (without _id, password_hash)
    for email, pw, name, role, dept_code in SEED_USERS:
        doc = {
            "id": str(uuid.uuid4()), "email": email.lower(),
            "password_hash": hash_password(pw), "name": name,
            "role": role, "department_id": dept_map[dept_code],
            "is_active": True, "created_at": now.isoformat()
        }
        await db.users.insert_one(doc)
        user_map[email.lower()] = {"id": doc["id"], "name": name, "email": email.lower(), "role": role, "department_id": doc["department_id"]}
    logger.info(f"  {len(user_map)} users created.")

    # ── 4. Assign Approver Chains ──
    assign_count = 0
    for (dept_code, form_name), approvers in APPROVER_ASSIGNMENTS.items():
        key = (dept_code, form_name)
        tmpl = tmpl_lookup.get(key)
        if not tmpl:
            continue
        chain = []
        for approver_email, step in approvers:
            u = user_map.get(approver_email.lower())
            if u:
                chain.append({"step": step, "user_id": u["id"], "user_name": u["name"]})
        chain.sort(key=lambda x: x["step"])
        if chain:
            await db.form_templates.update_one({"id": tmpl["id"]}, {"$set": {"approver_chain": chain}})
            tmpl["approver_chain"] = chain
            assign_count += 1
    logger.info(f"  {assign_count} form templates assigned approvers.")

    # ── 5. Sample Requests ──
    req_count = 0
    notif_docs = []

    for idx, (req_email, dept_code, form_name, title, form_data, priority, status_flag, days_ago) in enumerate(SAMPLE_REQUESTS):
        tmpl = tmpl_lookup.get((dept_code, form_name))
        if not tmpl:
            logger.warning(f"  Template not found: ({dept_code}, {form_name})")
            continue
        requester = user_map.get(req_email.lower())
        if not requester:
            logger.warning(f"  User not found: {req_email}")
            continue

        created_at = (now - timedelta(days=days_ago, hours=random.randint(1, 12), minutes=random.randint(0, 59))).isoformat()
        chain = tmpl.get("approver_chain", [])

        # Build approvals based on status_flag
        approvals = []
        status = "in_progress"
        current_step = 1

        if not chain:
            # No approvers = auto-approved
            status = "approved"
            current_step = 0
        elif status_flag == "approved":
            # All steps approved
            for a in chain:
                acted = (now - timedelta(days=max(0, days_ago - a["step"]), hours=random.randint(1, 8))).isoformat()
                approvals.append({
                    "step": a["step"], "approver_id": a["user_id"], "approver_name": a["user_name"],
                    "status": "approved", "comments": random.choice(["Approved.", "Looks good.", "OK, proceed.", ""]),
                    "acted_at": acted
                })
            status = "approved"
            current_step = len(chain)
        elif status_flag == "rejected":
            # First approver rejected
            acted = (now - timedelta(days=max(0, days_ago - 1), hours=3)).isoformat()
            approvals.append({
                "step": 1, "approver_id": chain[0]["user_id"], "approver_name": chain[0]["user_name"],
                "status": "rejected", "comments": "Budget not justified. Please revise and resubmit with updated quotes.",
                "acted_at": acted
            })
            for a in chain[1:]:
                approvals.append({
                    "step": a["step"], "approver_id": a["user_id"], "approver_name": a["user_name"],
                    "status": "waiting", "comments": "", "acted_at": None
                })
            status = "rejected"
            current_step = 1
        elif status_flag == "in_progress_step2":
            # Step 1 approved, step 2 pending
            if len(chain) >= 2:
                acted = (now - timedelta(days=max(0, days_ago - 1), hours=5)).isoformat()
                approvals.append({
                    "step": 1, "approver_id": chain[0]["user_id"], "approver_name": chain[0]["user_name"],
                    "status": "approved", "comments": "Approved, forwarding to VP.", "acted_at": acted
                })
                approvals.append({
                    "step": 2, "approver_id": chain[1]["user_id"], "approver_name": chain[1]["user_name"],
                    "status": "pending", "comments": "", "acted_at": None
                })
                current_step = 2
            else:
                # Fallback if only 1 approver
                approvals.append({
                    "step": 1, "approver_id": chain[0]["user_id"], "approver_name": chain[0]["user_name"],
                    "status": "pending", "comments": "", "acted_at": None
                })
                current_step = 1
            status = "in_progress"
        else:
            # Default: in_progress, step 1 pending
            for a in chain:
                approvals.append({
                    "step": a["step"], "approver_id": a["user_id"], "approver_name": a["user_name"],
                    "status": "pending" if a["step"] == 1 else "waiting",
                    "comments": "", "acted_at": None
                })
            status = "in_progress"
            current_step = 1

        req_num = f"REQ-{idx + 1:05d}"
        req_doc = {
            "id": str(uuid.uuid4()), "request_number": req_num,
            "form_template_id": tmpl["id"], "form_template_name": tmpl["name"],
            "department_id": dept_map[dept_code],
            "requester_id": requester["id"], "requester_name": requester["name"],
            "requester_email": requester["email"],
            "title": title, "form_data": form_data,
            "notes": "", "priority": priority,
            "status": status, "current_approval_step": current_step,
            "total_approval_steps": len(chain),
            "approvals": approvals,
            "created_at": created_at, "updated_at": created_at
        }
        await db.requests.insert_one(req_doc)
        req_count += 1

        # Generate notifications
        if status == "approved":
            notif_docs.append({
                "id": str(uuid.uuid4()), "user_id": requester["id"],
                "request_id": req_doc["id"], "request_number": req_num,
                "message": f"Your request '{title}' has been fully approved!",
                "type": "request_approved", "is_read": random.choice([True, True, False]),
                "created_at": created_at
            })
        elif status == "rejected":
            notif_docs.append({
                "id": str(uuid.uuid4()), "user_id": requester["id"],
                "request_id": req_doc["id"], "request_number": req_num,
                "message": f"Your request '{title}' was rejected by {approvals[0]['approver_name']}",
                "type": "request_rejected", "is_read": False,
                "created_at": created_at
            })
        elif status == "in_progress" and approvals:
            pending_approver = next((a for a in approvals if a["status"] == "pending"), None)
            if pending_approver:
                notif_docs.append({
                    "id": str(uuid.uuid4()), "user_id": pending_approver["approver_id"],
                    "request_id": req_doc["id"], "request_number": req_num,
                    "message": f"Request '{title}' from {requester['name']} requires your approval",
                    "type": "approval_required", "is_read": False,
                    "created_at": created_at
                })

    if notif_docs:
        await db.notifications.insert_many(notif_docs)
    logger.info(f"  {req_count} sample requests created with {len(notif_docs)} notifications.")

    # ── 6. Indexes ──
    await db.users.create_index("id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.departments.create_index("id", unique=True)
    await db.departments.create_index("code", unique=True)
    await db.form_templates.create_index("id", unique=True)
    await db.form_templates.create_index("department_id")
    await db.requests.create_index("id", unique=True)
    await db.requests.create_index("requester_id")
    await db.requests.create_index("department_id")
    await db.requests.create_index("status")
    await db.requests.create_index([("created_at", -1)])
    await db.notifications.create_index("id", unique=True)
    await db.notifications.create_index("user_id")
    await db.notifications.create_index([("user_id", 1), ("is_read", 1)])

    logger.info("Seeding complete!")
    logger.info(f"  Summary: {len(dept_map)} depts, {tmpl_count} templates, {len(user_map)} users, {assign_count} approver chains, {req_count} requests, {len(notif_docs)} notifications")
