CREATE DATABASE IF NOT EXISTS multivendor_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE multivendor_db;

CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(30) NOT NULL UNIQUE
);

INSERT INTO roles (name)
VALUES ('super_admin'), ('vendor'), ('customer')
ON DUPLICATE KEY UPDATE name = VALUES(name);

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    role_id INT NOT NULL,
    reset_token_hash VARCHAR(255) NULL,
    reset_token_expires_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_role_id FOREIGN KEY (role_id) REFERENCES roles(id)
);

CREATE INDEX ix_users_email ON users(email);

CREATE TABLE vendors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    business_name VARCHAR(180) NOT NULL,
    gst_number VARCHAR(30) NOT NULL UNIQUE,
    contact_number VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_vendors_user_id FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    description TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX ix_categories_name ON categories(name);

CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(180) NOT NULL,
    description TEXT NOT NULL,
    category_id INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    vendor_id INT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_category_id FOREIGN KEY (category_id) REFERENCES categories(id),
    CONSTRAINT fk_products_vendor_id FOREIGN KEY (vendor_id) REFERENCES vendors(id),
    CONSTRAINT chk_products_price CHECK (price > 0),
    CONSTRAINT chk_products_quantity CHECK (quantity >= 0)
);

CREATE INDEX ix_products_name ON products(name);

CREATE TABLE carts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_carts_user_id FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE cart_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cart_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_cart_items_cart_id FOREIGN KEY (cart_id) REFERENCES carts(id),
    CONSTRAINT fk_cart_items_product_id FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT uq_cart_product UNIQUE (cart_id, product_id),
    CONSTRAINT chk_cart_items_quantity CHECK (quantity > 0)
);

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    total_amount DECIMAL(10, 2) NOT NULL,
    shipping_address TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_orders_user_id FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT chk_orders_total_amount CHECK (total_amount >= 0)
);

CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    vendor_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    CONSTRAINT fk_order_items_order_id FOREIGN KEY (order_id) REFERENCES orders(id),
    CONSTRAINT fk_order_items_product_id FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT fk_order_items_vendor_id FOREIGN KEY (vendor_id) REFERENCES vendors(id),
    CONSTRAINT chk_order_items_quantity CHECK (quantity > 0),
    CONSTRAINT chk_order_items_unit_price CHECK (unit_price > 0),
    CONSTRAINT chk_order_items_subtotal CHECK (subtotal >= 0)
);

CREATE TABLE payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    user_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    method VARCHAR(40) NOT NULL DEFAULT 'mock',
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    transaction_reference VARCHAR(120) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_payments_order_id FOREIGN KEY (order_id) REFERENCES orders(id),
    CONSTRAINT fk_payments_user_id FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT chk_payments_amount CHECK (amount >= 0)
);

CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    rating INT NOT NULL,
    comment TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_reviews_user_id FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_reviews_product_id FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT uq_review_user_product UNIQUE (user_id, product_id),
    CONSTRAINT chk_reviews_rating CHECK (rating BETWEEN 1 AND 5)
);

CREATE TABLE wishlists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_wishlists_user_id FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_wishlists_product_id FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT uq_wishlist_user_product UNIQUE (user_id, product_id)
);

CREATE TABLE inventory_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    vendor_id INT NOT NULL,
    quantity INT NOT NULL,
    action VARCHAR(40) NOT NULL,
    note TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_inventory_logs_product_id FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT fk_inventory_logs_vendor_id FOREIGN KEY (vendor_id) REFERENCES vendors(id),
    CONSTRAINT chk_inventory_logs_quantity CHECK (quantity > 0)
);

CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(80) NOT NULL,
    entity_type VARCHAR(80) NULL,
    entity_id INT NULL,
    details TEXT NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_logs_user_id FOREIGN KEY (user_id) REFERENCES users(id)
);

