Extract structured data from invoices into JSON.

The invoice contains vendor information, client details, line items with quantities and rates, and totals including tax. The output must be a flat JSON object with nested line_items array.

Key fields to extract: vendor name, invoice number, dates, client name, contact person, line items (description, quantity, unit, rate, amount), subtotal, tax rate, tax amount, total, and currency.

All monetary values should be numbers. Dates should be YYYY-MM-DD format.
