-- ==============================================================================
-- Customer Service AI Platform - Seed Data
-- ==============================================================================

-- 1. Insert Customers
INSERT INTO customers (id, phone_number, email, full_name, metadata)
VALUES
    ('a0000000-0000-0000-0000-000000000001', '+1234567890', 'john.doe@example.com', 'John Doe', '{"vip": true, "language": "en"}'::jsonb),
    ('a0000000-0000-0000-0000-000000000002', '+1987654321', 'sarah.connor@example.com', 'Sarah Connor', '{"vip": false, "language": "en"}'::jsonb),
    ('a0000000-0000-0000-0000-000000000003', '+1122334455', 'alex.smith@example.com', 'Alex Smith', '{"vip": false, "language": "en"}'::jsonb)
ON CONFLICT (phone_number) DO NOTHING;

-- 2. Insert Orders
INSERT INTO orders (order_number, customer_id, status, total_amount, currency, carrier, tracking_number, estimated_delivery, items)
VALUES
    (
        'ORD-1001',
        'a0000000-0000-0000-0000-000000000001',
        'shipped',
        149.99,
        'USD',
        'DHL Express',
        'DHL-992817263',
        CURRENT_DATE + INTERVAL '2 days',
        '[{"name": "Wireless Noise Cancelling Headphones", "quantity": 1, "price": 149.99}]'::jsonb
    ),
    (
        'ORD-1002',
        'a0000000-0000-0000-0000-000000000001',
        'delivered',
        49.50,
        'USD',
        'FedEx',
        'FDX-11827364',
        CURRENT_DATE - INTERVAL '3 days',
        '[{"name": "Ergonomic Memory Foam Mousepad", "quantity": 1, "price": 19.50}, {"name": "USB-C Fast Charging Cable (2-Pack)", "quantity": 1, "price": 30.00}]'::jsonb
    ),
    (
        'ORD-1003',
        'a0000000-0000-0000-0000-000000000002',
        'processing',
        399.00,
        'USD',
        'UPS Ground',
        'UPS-88273619',
        CURRENT_DATE + INTERVAL '5 days',
        '[{"name": "4K Ultra-HD Monitor 27-inch", "quantity": 1, "price": 399.00}]'::jsonb
    )
ON CONFLICT (order_number) DO NOTHING;

-- 3. Insert Knowledge Base / FAQs
INSERT INTO knowledge_base (category, question, answer, keywords)
VALUES
    (
        'returns',
        'What is your return and refund policy?',
        'We offer a 30-day hassle-free return window for all unused items in their original packaging. Once we receive your item, refunds are processed to your original payment method within 3-5 business days.',
        ARRAY['return', 'refund', 'policy', 'money back', 'exchange', '30 days']
    ),
    (
        'shipping',
        'How long does standard and express shipping take?',
        'Standard shipping takes 3 to 5 business days. Express shipping takes 1 to 2 business days. Free standard shipping is available on all orders over $50.',
        ARRAY['shipping', 'delivery', 'standard shipping', 'express', 'how long', 'carrier', 'tracking']
    ),
    (
        'warranty',
        'Do products come with a warranty?',
        'All hardware products include a 1-year limited manufacturer warranty covering hardware defects and malfunctions. Extended 2-year and 3-year protection plans are also available at checkout.',
        ARRAY['warranty', 'defect', 'broken', 'repair', 'guarantee', 'replacement']
    ),
    (
        'payment',
        'What payment methods do you accept?',
        'We accept all major credit/debit cards (Visa, MasterCard, American Express), PayPal, Apple Pay, Google Pay, and Klarna pay-in-4 installments.',
        ARRAY['payment', 'credit card', 'paypal', 'apple pay', 'installment', 'klarna']
    );
