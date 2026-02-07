import uuid
from datetime import datetime, timezone
from utils.helpers import hash_password
import logging

logger = logging.getLogger(__name__)

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
        {"name": "Demo Unit", "fields": [
            {"name": "unit_model", "label": "Unit Model", "type": "text", "required": True},
            {"name": "customer", "label": "Customer", "type": "text", "required": True},
            {"name": "demo_date", "label": "Demo Date", "type": "date", "required": True},
            {"name": "location", "label": "Location", "type": "text", "required": True}
        ]},
        {"name": "Brand New to Demo", "fields": [
            {"name": "unit_model", "label": "Unit Model", "type": "text", "required": True},
            {"name": "serial_number", "label": "Serial Number", "type": "text", "required": True},
            {"name": "reason", "label": "Reason", "type": "textarea", "required": True}
        ]},
        {"name": "Showing", "fields": [
            {"name": "product", "label": "Product", "type": "text", "required": True},
            {"name": "customer", "label": "Customer", "type": "text", "required": True},
            {"name": "date", "label": "Date", "type": "date", "required": True}
        ]},
        {"name": "Sample for Evaluation", "fields": [
            {"name": "product", "label": "Product", "type": "text", "required": True},
            {"name": "customer", "label": "Customer", "type": "text", "required": True},
            {"name": "evaluation_period", "label": "Evaluation Period (days)", "type": "number", "required": True}
        ]},
        {"name": "Loaner Tool", "fields": [
            {"name": "tool", "label": "Tool Description", "type": "text", "required": True},
            {"name": "borrower", "label": "Borrower", "type": "text", "required": True},
            {"name": "date_from", "label": "From", "type": "date", "required": True},
            {"name": "date_to", "label": "To", "type": "date", "required": True}
        ]},
        {"name": "Pull Out", "fields": [
            {"name": "item", "label": "Item", "type": "text", "required": True},
            {"name": "location", "label": "From Location", "type": "text", "required": True},
            {"name": "reason", "label": "Reason", "type": "textarea", "required": True}
        ]},
        {"name": "Request for Technician (Demo)", "fields": [
            {"name": "product", "label": "Product", "type": "text", "required": True},
            {"name": "customer", "label": "Customer", "type": "text", "required": True},
            {"name": "date", "label": "Date Needed", "type": "date", "required": True},
            {"name": "location", "label": "Location", "type": "text", "required": True}
        ]},
        {"name": "Repair at Site", "fields": [
            {"name": "unit_model", "label": "Unit Model", "type": "text", "required": True},
            {"name": "issue", "label": "Issue Description", "type": "textarea", "required": True},
            {"name": "customer", "label": "Customer", "type": "text", "required": True},
            {"name": "site_address", "label": "Site Address", "type": "text", "required": True}
        ]},
        {"name": "Item for Replacement", "fields": [
            {"name": "item", "label": "Item", "type": "text", "required": True},
            {"name": "reason", "label": "Reason for Replacement", "type": "textarea", "required": True},
            {"name": "customer", "label": "Customer", "type": "text", "required": True}
        ]},
        {"name": "FOC", "fields": [
            {"name": "item", "label": "Item", "type": "text", "required": True},
            {"name": "customer", "label": "Customer", "type": "text", "required": True},
            {"name": "reason", "label": "Reason", "type": "textarea", "required": True}
        ]},
        {"name": "Manual Entry", "fields": [
            {"name": "entry_type", "label": "Entry Type", "type": "text", "required": True},
            {"name": "details", "label": "Details", "type": "textarea", "required": True}
        ]},
        {"name": "Price Approval Form", "fields": [
            {"name": "product", "label": "Product", "type": "text", "required": True},
            {"name": "standard_price", "label": "Standard Price", "type": "number", "required": True},
            {"name": "requested_price", "label": "Requested Price", "type": "number", "required": True},
            {"name": "customer", "label": "Customer", "type": "text", "required": True},
            {"name": "justification", "label": "Justification", "type": "textarea", "required": True}
        ]},
        {"name": "Cash Float", "fields": [
            {"name": "amount", "label": "Amount", "type": "number", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}
        ]},
        {"name": "Customer Order (PO/Check to Follow)", "fields": [
            {"name": "customer", "label": "Customer", "type": "text", "required": True},
            {"name": "items", "label": "Items Ordered", "type": "textarea", "required": True},
            {"name": "total_amount", "label": "Total Amount", "type": "number", "required": True},
            {"name": "payment_terms", "label": "Payment Terms", "type": "text", "required": True}
        ]},
        {"name": "Advance Stocking (TRQ)", "fields": [
            {"name": "items", "label": "Items", "type": "textarea", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "reason", "label": "Reason", "type": "textarea", "required": True}
        ]},
    ],
    "DSC": [
        {"name": "Cash Float - Budget For Billable PMS", "fields": [
            {"name": "amount", "label": "Amount", "type": "number", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}
        ]},
        {"name": "Re-Ordering Of Stock - Unit & Accessories", "fields": [
            {"name": "items", "label": "Items", "type": "textarea", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "text", "required": True},
            {"name": "current_stock", "label": "Current Stock Level", "type": "text", "required": False}
        ]},
        {"name": "Re-Ordering Of Spareparts - Repairs", "fields": [
            {"name": "parts", "label": "Spare Parts Needed", "type": "textarea", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "text", "required": True}
        ]},
        {"name": "Provisional & Collection Receipts", "fields": [
            {"name": "receipt_type", "label": "Receipt Type", "type": "select", "required": True, "options": ["Provisional", "Collection"]},
            {"name": "customer", "label": "Customer", "type": "text", "required": True},
            {"name": "amount", "label": "Amount", "type": "number", "required": True}
        ]},
        {"name": "Delivery Receipts & Cash Invoice", "fields": [
            {"name": "customer", "label": "Customer", "type": "text", "required": True},
            {"name": "items", "label": "Items", "type": "textarea", "required": True},
            {"name": "amount", "label": "Amount", "type": "number", "required": True}
        ]},
        {"name": "Store Use - Consumables & Non Consumables", "fields": [
            {"name": "item_type", "label": "Type", "type": "select", "required": True, "options": ["Consumable", "Non-Consumable"]},
            {"name": "items", "label": "Items", "type": "textarea", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "text", "required": True}
        ]},
    ],
    "MCG": [
        {"name": "Item Replacement", "fields": [
            {"name": "item", "label": "Item", "type": "text", "required": True},
            {"name": "reason", "label": "Reason", "type": "textarea", "required": True},
            {"name": "outlet", "label": "Outlet", "type": "text", "required": True}
        ]},
        {"name": "Item Use for Event (Caravan)", "fields": [
            {"name": "items", "label": "Items Needed", "type": "textarea", "required": True},
            {"name": "event", "label": "Event Name", "type": "text", "required": True},
            {"name": "date", "label": "Event Date", "type": "date", "required": True}
        ]},
        {"name": "Technician Request", "fields": [
            {"name": "issue", "label": "Issue Description", "type": "textarea", "required": True},
            {"name": "location", "label": "Location", "type": "text", "required": True},
            {"name": "date_needed", "label": "Date Needed", "type": "date", "required": True}
        ]},
    ],
    "ACCT": [
        {"name": "Barcode Stickers for MCG Outlets", "fields": [
            {"name": "outlet", "label": "Outlet", "type": "text", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "product_list", "label": "Product List", "type": "textarea", "required": True}
        ]},
    ],
    "PUR": [
        {"name": "Special Discount", "fields": [
            {"name": "product", "label": "Product", "type": "text", "required": True},
            {"name": "standard_price", "label": "Standard Price", "type": "number", "required": True},
            {"name": "requested_discount", "label": "Requested Discount %", "type": "number", "required": True},
            {"name": "reason", "label": "Reason", "type": "textarea", "required": True}
        ]},
        {"name": "Product Sample / Own Use", "fields": [
            {"name": "product", "label": "Product", "type": "text", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "select", "required": True, "options": ["Sample", "Own Use"]}
        ]},
        {"name": "Product Demo", "fields": [
            {"name": "product", "label": "Product", "type": "text", "required": True},
            {"name": "customer", "label": "Customer", "type": "text", "required": True},
            {"name": "demo_date", "label": "Demo Date", "type": "date", "required": True}
        ]},
        {"name": "Local Buy Out", "fields": [
            {"name": "item", "label": "Item Description", "type": "textarea", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "estimated_cost", "label": "Estimated Cost", "type": "number", "required": True},
            {"name": "supplier", "label": "Preferred Supplier", "type": "text", "required": False}
        ]},
        {"name": "Representation", "fields": [
            {"name": "event", "label": "Event/Meeting", "type": "text", "required": True},
            {"name": "date", "label": "Date", "type": "date", "required": True},
            {"name": "budget", "label": "Budget", "type": "number", "required": True},
            {"name": "details", "label": "Details", "type": "textarea", "required": True}
        ]},
        {"name": "Loaner Tools", "fields": [
            {"name": "tool", "label": "Tool", "type": "text", "required": True},
            {"name": "borrower", "label": "Borrower", "type": "text", "required": True},
            {"name": "duration", "label": "Duration (days)", "type": "number", "required": True}
        ]},
        {"name": "QC Reworks", "fields": [
            {"name": "product", "label": "Product", "type": "text", "required": True},
            {"name": "issue", "label": "QC Issue", "type": "textarea", "required": True},
            {"name": "quantity_affected", "label": "Quantity Affected", "type": "number", "required": True}
        ]},
    ],
    "HR": [
        {"name": "Manpower Request", "fields": [
            {"name": "position", "label": "Position", "type": "text", "required": True},
            {"name": "department", "label": "Department", "type": "text", "required": True},
            {"name": "headcount", "label": "Headcount", "type": "number", "required": True},
            {"name": "justification", "label": "Justification", "type": "textarea", "required": True}
        ]},
        {"name": "Leave Request", "fields": [
            {"name": "leave_type", "label": "Leave Type", "type": "select", "required": True, "options": ["Vacation", "Sick", "Emergency", "Maternity/Paternity", "Other"]},
            {"name": "date_from", "label": "Date From", "type": "date", "required": True},
            {"name": "date_to", "label": "Date To", "type": "date", "required": True},
            {"name": "reason", "label": "Reason", "type": "textarea", "required": True}
        ]},
        {"name": "Cash Advance Request", "fields": [
            {"name": "amount", "label": "Amount", "type": "number", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True},
            {"name": "repayment_terms", "label": "Repayment Terms", "type": "text", "required": True}
        ]},
        {"name": "Bank Loan Request", "fields": [
            {"name": "bank", "label": "Bank", "type": "text", "required": True},
            {"name": "amount", "label": "Amount", "type": "number", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}
        ]},
        {"name": "Health Benefit Reimbursement", "fields": [
            {"name": "claim_type", "label": "Claim Type", "type": "select", "required": True, "options": ["Medical", "Dental", "Vision", "Other"]},
            {"name": "amount", "label": "Amount", "type": "number", "required": True},
            {"name": "date_of_service", "label": "Date of Service", "type": "date", "required": True},
            {"name": "details", "label": "Details", "type": "textarea", "required": True}
        ]},
        {"name": "Flight Request (Official Travel)", "fields": [
            {"name": "destination", "label": "Destination", "type": "text", "required": True},
            {"name": "date_departure", "label": "Departure Date", "type": "date", "required": True},
            {"name": "date_return", "label": "Return Date", "type": "date", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}
        ]},
        {"name": "Educational Assistance Request", "fields": [
            {"name": "school", "label": "School/Institution", "type": "text", "required": True},
            {"name": "course", "label": "Course/Program", "type": "text", "required": True},
            {"name": "amount", "label": "Amount Requested", "type": "number", "required": True}
        ]},
        {"name": "COE Request", "fields": [
            {"name": "purpose", "label": "Purpose", "type": "select", "required": True, "options": ["Bank Requirement", "Visa Application", "Government", "Other"]},
            {"name": "details", "label": "Additional Details", "type": "textarea", "required": False}
        ]},
        {"name": "Pay Slip Request", "fields": [
            {"name": "period", "label": "Pay Period", "type": "text", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "text", "required": True}
        ]},
        {"name": "Office Supplies Request", "fields": [
            {"name": "items", "label": "Items Needed", "type": "textarea", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "text", "required": True}
        ]},
        {"name": "Equipment Supplies Request", "fields": [
            {"name": "equipment", "label": "Equipment", "type": "text", "required": True},
            {"name": "specifications", "label": "Specifications", "type": "textarea", "required": True}
        ]},
        {"name": "Uniform Request", "fields": [
            {"name": "size", "label": "Size", "type": "select", "required": True, "options": ["XS", "S", "M", "L", "XL", "XXL"]},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "type", "label": "Uniform Type", "type": "text", "required": True}
        ]},
        {"name": "Employee ID / Lanyard Issuance", "fields": [
            {"name": "type", "label": "Type", "type": "select", "required": True, "options": ["New ID", "Replacement ID", "Lanyard"]},
            {"name": "reason", "label": "Reason", "type": "text", "required": True}
        ]},
        {"name": "Purchase Order Form", "fields": [
            {"name": "vendor", "label": "Vendor", "type": "text", "required": True},
            {"name": "items", "label": "Items", "type": "textarea", "required": True},
            {"name": "total_amount", "label": "Total Amount", "type": "number", "required": True}
        ]},
        {"name": "Cash Float Slip Form (Petty Cash)", "fields": [
            {"name": "amount", "label": "Amount", "type": "number", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}
        ]},
        {"name": "Gate Pass Form", "fields": [
            {"name": "items", "label": "Items to Pass", "type": "textarea", "required": True},
            {"name": "destination", "label": "Destination", "type": "text", "required": True},
            {"name": "date", "label": "Date", "type": "date", "required": True}
        ]},
        {"name": "Vehicle Request", "fields": [
            {"name": "destination", "label": "Destination", "type": "text", "required": True},
            {"name": "date", "label": "Date", "type": "date", "required": True},
            {"name": "passengers", "label": "Number of Passengers", "type": "number", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}
        ]},
    ],
    "WHSE": [
        {"name": "Own Used (QC/WHSE/LOG)", "fields": [
            {"name": "item", "label": "Item", "type": "text", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "department", "label": "Department", "type": "select", "required": True, "options": ["QC", "Warehouse", "Logistics"]}
        ]},
        {"name": "Cash Float", "fields": [
            {"name": "amount", "label": "Amount", "type": "number", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "textarea", "required": True}
        ]},
        {"name": "Local Buy Out (Box/Tape/Etc)", "fields": [
            {"name": "item", "label": "Item", "type": "text", "required": True},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "estimated_cost", "label": "Estimated Cost", "type": "number", "required": True}
        ]},
        {"name": "Request for Sticker (Powertools/LCE/Etc)", "fields": [
            {"name": "product_line", "label": "Product Line", "type": "select", "required": True, "options": ["Powertools", "LCE", "Other"]},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
            {"name": "details", "label": "Details", "type": "textarea", "required": False}
        ]},
        {"name": "Request for Warranty Card (Powertools/LCE/Etc)", "fields": [
            {"name": "product_line", "label": "Product Line", "type": "select", "required": True, "options": ["Powertools", "LCE", "Other"]},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True}
        ]},
        {"name": "Request for Manual (Powertools/LCE/Etc)", "fields": [
            {"name": "product_line", "label": "Product Line", "type": "select", "required": True, "options": ["Powertools", "LCE", "Other"]},
            {"name": "quantity", "label": "Quantity", "type": "number", "required": True}
        ]},
        {"name": "Request for Manual DR (Completion)", "fields": [
            {"name": "dr_number", "label": "DR Number", "type": "text", "required": True},
            {"name": "details", "label": "Details", "type": "textarea", "required": True}
        ]},
    ],
}


async def seed_data(db):
    """Seed departments, form templates, and super admin user."""
    existing = await db.departments.count_documents({})
    if existing > 0:
        logger.info("Data already seeded, skipping.")
        return

    logger.info("Seeding initial data...")

    dept_map = {}
    for dept_data in DEPARTMENTS:
        dept = {
            "id": str(uuid.uuid4()),
            "name": dept_data["name"],
            "code": dept_data["code"],
            "description": dept_data["description"],
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.departments.insert_one(dept)
        dept_map[dept_data["code"]] = dept["id"]

    # Seed form templates
    for dept_code, forms in FORM_TEMPLATES.items():
        dept_id = dept_map.get(dept_code)
        if not dept_id:
            continue
        for form_data in forms:
            tmpl = {
                "id": str(uuid.uuid4()),
                "department_id": dept_id,
                "name": form_data["name"],
                "description": "",
                "fields": form_data["fields"],
                "approver_chain": [],
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.form_templates.insert_one(tmpl)

    # Seed super admin
    admin_dept = dept_map.get("GEN", list(dept_map.values())[0])
    admin = {
        "id": str(uuid.uuid4()),
        "email": "admin@company.com",
        "password_hash": hash_password("admin123"),
        "name": "Super Admin",
        "role": "super_admin",
        "department_id": admin_dept,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(admin)

    # Create indexes
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
    await db.notifications.create_index("id", unique=True)
    await db.notifications.create_index("user_id")

    logger.info(f"Seeded {len(DEPARTMENTS)} departments, {sum(len(v) for v in FORM_TEMPLATES.values())} form templates, and 1 super admin.")
