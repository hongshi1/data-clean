# DOCUMENTATION FOR DEENCRAFT(E-COMMERECE WEBSITE FOR DEENCRAFT)

![](images/128a6a8a3cd70cc0a98939672f60cce0b69ec944aa5688426380f7c2f7cc4e1a.jpg)

Abdul Qadeer Sikander

Tooba Javed

24014198-069

24014198-099

Hafsa Noor

## 24014198-118

M. Awais Safdar

## 24014198-268

Dania Basar 24814198-002

## TABLE OF CONTENTS

Section Heading Page   
No. No.   
1 INTRODUCTION 4   
1.1 Purpose of the System / What’s the Problem? 4   
1.2 Existing System 5   
1.3 Limitations of Existing System 6   
1.4 Proposed System 6   
1.5 Departments of the Proposed System 7   
2 ORGANIZATIONAL CHART 10   
2.1 Scope of the System 10   
2.2 Phases in Terms of Scope 10   
2.3 User Roles in the System 13   
2.4 Summary of Initial Requirements 15   
3 IDENTIFYING EXTERNAL ENTITIES 16   
3.1 Refined External Entities 17   
3.2 Removed / Merged Entities During Refinement 17   
3.2.1 Context Level Data Flow Diagram 17   
4 DFD DIAGRAM 19   
5 REQUIREMENTS 20   
5.1 Functional Requirements 20   
5.2 Non-Functional Requirements 29   
6 ALLOCATED REQUIREMENTS 33   
7 PRIORITIES REQUIREMENTS 38   
8 REQUIREMENTS TRACEABILITY 46   
9 USE CASE DESCRIPTION & DIAGRAMS 54   
9.1 Module 1: Authentication Module 54   
9.2 Module 2: Catalog & Customization 56   
9.3 Module 3: Cart & Checkout 58   
9.4 Module 4: Order Management 61   
9.5 Module 5: Inventory Management 62   
9.6 Module 6: Review & Rating Module 63   
9.7 Module 7: Dashboard & System Admin Module 65   
9.8 Module 8: Communication & Notification Engine 68   
9.9 System Diagram 70

## 1. Introduction

Deen Craft is a business that provides Islamic and customized products such as Prayer Mats, Tasbeeh, Digital Counters, Travel Mats. At the current stage, most business operations are handled manually through WhatsApp communication. Customers contact the business owner to ask about products, customization details, prices, and delivery information.

Although this method works for a small number of customers, it becomes difficult to manage when the number of orders increases, especially during busy Islamic occasions such as Ramadan and Eid. The business owner faces problems such as delayed replies, missed customer messages, confusion in customized orders, and difficulty managing inventory.

The current system also lacks proper order tracking and organized customer records. Customers often contact the owner repeatedly for order updates because there is no automated notification or tracking system.

To solve these problems, Deen Craft requires a proper web-based e-commerce system that can automate customer ordering, product customization, inventory management, and order tracking. The proposed website will provide customers with a simple, secure, and mobile-friendly shopping experience.

The system will also support important business features such as Cash on Delivery (COD), WhatsApp or SMS notifications, review management, discount offers, and inventory alerts. The platform will combine Islamic and modern design elements to create a professional and attractive online presence for the business.

## 1.1 Purpose of the System / What’s the problem?

The main purpose of the Deen Craft system is to convert the current manual ordering process into a complete online e-commerce platform. The website will allow customers to browse products, customize items, place orders, and track deliveries without depending on manual WhatsApp communication.

The system will help improve customer experience by providing organized product categories, proper product descriptions, secure login functionality, and a smooth checkout process. Customers will be able to independently explore products and place orders at any time.

Another important purpose of the system is to reduce human errors in customization and order handling. Since Deen Craft specializes in personalized products, the proposed system will provide structured customization forms where customers can easily enter names, select colors, choose fonts, and review customization details before confirming orders.

The system will also help the business owner manage inventory, customer records, promotional campaigns, and order processing more efficiently. Automated notifications and tracking features will reduce workload and improve communication with customers.

## 1.2 Existing System

## Overview of Existing System

Currently, Deen Craft operates through a manual business process using WhatsApp as the main communication platform. Customers contact the business owner to inquire about products, customization options, pricing details, and order-related information.

The owner manually handles all customer interactions, including responding to queries, sharing product images, noting customization requirements, and recording order details. Since all operations are done manually, the process becomes time-consuming and difficult to manage, especially during peak business periods.

## Working of Existing System

The working of the current system is entirely manual and communication-based. The process includes the following steps:

 Customers initiate contact through WhatsApp.

 The owner shares product images, prices, and available customization options.

 Customers provide customization details such as names, colors, font styles, and design preferences through chat messages.

 The owner manually records all order details and confirms the order with the customer.

 Delivery information is collected through chat after order confirmation.

 Payments are usually made via Cash on Delivery (COD).

 Customers frequently contact the owner for order updates, as there is no automated tracking system.

## 1.3 Limitations of Existing System

## 1. Manual Communication Dependency

The system relies completely on manual WhatsApp communication, which is time-consuming and increases the workload on the business owner.

## 2. Risk of Missed or Delayed Responses

Due to high message volume, especially during peak seasons, there is a higher chance of missed messages and delayed replies to customers.

## 3. Lack of Inventory Management

There is no automated inventory system, which can lead to accepting orders for items that are out of stock.

## 4. No Order Tracking System

Customers cannot track their orders online and must repeatedly contact the owner for updates, increasing unnecessary communication.

## 5. No Centralized Data Management

Customer details, customization requirements, and order records are stored manually, making data management disorganized and difficult to maintain.

## 6. Difficulty During Peak Seasons

During busy periods like Ramadan and Eid, managing a large number of orders becomes overwhelming and increases the chances of errors in order handling.

## 1.4 Proposed System

The proposed system is a complete web-based e-commerce platform specially designed for Deen Craft. The system will automate the entire customer ordering and management process.

The website will allow customers to:

 Create accounts using mobile number or email verification.

 Browse products as guests.

 View detailed product information.

 Customize products before purchase.

 Add products to shopping cart.

 Place orders using Cash on Delivery.

 Track order status online.

 Receive WhatsApp or SMS notifications.

 Submit product reviews and ratings.

 Apply promotional discount coupons.

The system will also provide an admin dashboard where the business owner can:

 Add, edit, or delete products.

 Manage inventory and stock alerts.

 View and process customer orders.

 Approve or reject customer reviews.

 Manage discounts and promotional campaigns.

 Monitor sales performance and analytics.

 Configure delivery charges and customization settings.

 Manage notifications and order tracking.

The proposed solution will significantly reduce manual workload while improving accuracy, speed, and customer satisfaction.

## 1.5 Departments of the Proposed System

## 1. User Management Department

The User Management Department handles customer registration, login, authentication, password recovery, and account security. Users can create accounts using either a mobile number or email address.

The system also supports OTP verification and secure session management. Customers will be able to manage their personal information, addresses, and order history through their accounts.

## 2. Product Management Department

The Product Management Department manages all products available on the website. The admin can add, edit, or remove products along with product images, descriptions, categories, and prices.

This department also handles product organization for categories such as Prayer Mats, Tasbeeh, Digital Counters, Travel Mats, Islamic Wall Art, and Gift Products.

## 3. Product Customization Department

The Product Customization Department is one of the most important modules of the system. It allows customers to personalize products according to their preferences.

Customers can enter custom names or text, select colors, choose fonts, and configure other customization options. The system validates character limits and ensures all required customization details are completed before the order is confirmed.

## 4. Shopping Cart and Checkout Department

This department handles shopping cart operations and the checkout process. Customers can add products to the cart, update quantities, remove products, and apply promotional discount coupons.

The checkout process includes shipping details, payment method selection, order review, and final order confirmation. Cash on Delivery will remain the default payment method.

## 5. Order Management Department

The Order Management Department manages order processing, order tracking, and status updates. Each order is assigned a unique tracking ID.

The department also handles order statuses such as Pending, Confirmed, Processing, Dispatched, Delivered, and Cancelled. Customers can track their orders online using the tracking system.

## 6. Inventory Management Department

The Inventory Management Department monitors stock levels and product availability. The system automatically detects low-stock and out-of-stock situations.

Admins receive alerts when stock levels become low or when customers place orders for unavailable products. This department helps improve inventory accuracy and reduces stockrelated problems.

## 7. Notification Management Department

This department manages all notifications sent to customers and admins. The system automatically sends order confirmations, dispatch updates, cancellation messages, and OTP notifications.

Notifications are mainly delivered through WhatsApp and SMS because most customers prefer mobile communication over email.

## 8. Review and Rating Department

The Review and Rating Department allows customers to submit product reviews and ratings after receiving their orders.

The system supports review moderation where all reviews remain pending until approved by the admin. Verified purchase labels help increase customer trust and improve product credibility.

## 9. Admin Management Department

The Admin Management Department provides a centralized dashboard for managing the complete website.

The admin can manage products, inventory, customer orders, promotional campaigns, customer reviews, and sales reports from a single interface. The dashboard is designed to be simple and user-friendly so that non-technical users can operate it easily.

# 2. ORGANIZATIONAL CHART BASED ON ABOVE MENTIONED DEPARTMENTS:

![](images/ffd2549d700338f51782bd8fcffe399c933346b93cb24c5218101aeae484f805.jpg)

## 2.1 Scope of the System

## Customer Side Scope

The customer side of the system includes:

 User registration and login.

 OTP-based login support.

 Product browsing and searching.

 Product filtering and sorting.

 Product customization.

 Shopping cart management.

 Checkout process.

 Cash on Delivery support.

 Order tracking.

 Review and rating system.

 Order cancellation.

 WhatsApp and SMS notifications.

## Admin Side Scope

The admin side of the system includes:

 Product management.

 Category management.

 Inventory management.

 Order management.

 Customer management.

 Review moderation.

 Promotional campaign management.

 Analytics dashboard.

 Maintenance mode management.

 Export reports.

 Notification management.

## 2.2 Phases in terms of scope:

The Deen Craft E-Commerce System is divided into three phases. Each phase covers different business areas according to the business growth and automation requirements.

## Phase I

Phase I focuses on the core functionalities required to launch the online customized Islamic products store. This phase includes the main customer-facing operations and essential admin management features.

Phase I includes the following business areas:

 User Management

 Product Management

 Product Customization

 Shopping Cart and Checkout

 Order Processing and Tracking

 Inventory Management

 Notification Management

 Review and Rating System

Basic Admin Dashboard

This document scope is limited to Phase I only.

## Phase II

Phase II focuses on improving business operations, customer engagement, and management automation. This phase introduces advanced reporting and marketing features.

Phase II includes the following business areas:

 CRM (Customer Relationship Management)

 Advanced Sales Reports and Analytics

 Promotional Campaign Management

 Discount and Coupon Management

 Customer Support Management

 Advanced Inventory Reporting

 Multi-Admin Management

 Supplier and Vendor Management

 Automated Reordering System

## Phase III

Phase III provides a complete enterprise-level solution for Deen Craft with advanced integrations and scalability features. This phase covers all remaining business areas not implemented in previous phases.

Phase III includes the following business areas:

 Online Payment Gateway Integration

 Mobile Application Integration

 AI-Based Product Recommendations

 Delivery API Integration

 Real-Time Shipment Tracking

 Multi-Language Support

 International Shipping Support

 Advanced Security and Fraud Detection

 Business Intelligence and Forecasting

 Cloud Backup and Disaster Recovery System

## 2.3 User Roles in the System

## 1. Customer

Customers can:

 Register accounts.

 Browse products.

 Customize products.

 Add products to cart.

 Place orders.

 Track orders.

 Submit reviews.

 Cancel orders.

## 2. Guest User

Guest users can:

 Browse products.

 View product details.

 Search products.

Guest users cannot:

 Add products to cart.

 Place orders.

 Access checkout.

## 3. Admin

The Admin can:

 Manage products.

 Manage inventory.

 Process orders.

 Approve reviews.

 Manage discounts.

 Monitor analytics.

 Configure system settings.

Initially, the system supports only one admin account.

## 2.4 Summary of Initial Requirements

## User Registration and Login

o Users must be able to register using email or mobile number.

o OTP verification and secure login functionality must be supported.

## Product Browsing and Search

o Customers should be able to browse product categories and search products easily.

## Product Customization

o Customers should be able to customize prayer mats, tasbeehs, and other products by entering names, selecting colors, fonts, and materials.

## Shopping Cart and Checkout

o Users must be able to add products to cart, update quantities, and place orders using Cash on Delivery (COD).

## Order Tracking

o Customers should be able to track order status online using Tracking ID.

## Inventory Management

o Admin should be able to manage stock levels and receive low-stock alerts.

## Notification System

o The system should send WhatsApp/SMS notifications for OTPs, order confirmations, dispatch updates, and cancellations.

## Review and Rating System

o Customers should be able to submit reviews and ratings after delivery.

## Admin Dashboard

o Admin should be able to manage products, orders, inventory, discounts, and analytics from a centralized dashboard.

## 3. Identifying External Entities

The identification of external entities for the Deen Craft E-Commerce System is based on the business abstract and system requirements. External entities are the people, organizations, or external systems that interact with the system but are not part of the internal processing system. The identification process is completed in two phases.

## a. Over Specify Entities from Abstract

Based on the project abstract and client requirements, the following possible external entities are identified:

<table><tr><td rowspan=1 colspan=1>Possible Entity</td><td rowspan=1 colspan=1>Reason for Identification</td></tr><tr><td rowspan=1 colspan=1>Customer</td><td rowspan=1 colspan=1>Purchases and customizes products</td></tr><tr><td rowspan=1 colspan=1>Guest User</td><td rowspan=1 colspan=1>Browses products without login</td></tr><tr><td rowspan=1 colspan=1>Admin</td><td rowspan=1 colspan=1>Manages the complete system</td></tr><tr><td rowspan=1 colspan=1>Delivery Rider/Courier</td><td rowspan=1 colspan=1>Delivers customer orders</td></tr><tr><td rowspan=1 colspan=1>WhatsApp API</td><td rowspan=1 colspan=1>Sends OTPs and order notifications</td></tr><tr><td rowspan=1 colspan=1>SMS Service</td><td rowspan=1 colspan=1>Sends verification and alerts</td></tr><tr><td rowspan=1 colspan=1>Email Service</td><td rowspan=1 colspan=1>Sends order and account emails</td></tr><tr><td rowspan=1 colspan=1>Payment System</td><td rowspan=1 colspan=1>Handles payment process</td></tr><tr><td rowspan=1 colspan=1>Inventory Staff</td><td rowspan=1 colspan=1>Monitors stock and availability</td></tr><tr><td rowspan=1 colspan=1>Marketing Team</td><td rowspan=1 colspan=1>Manages promotions and discounts</td></tr><tr><td rowspan=1 colspan=1>Review System</td><td rowspan=1 colspan=1>Handles customer feedback</td></tr><tr><td rowspan=1 colspan=1>Database</td><td rowspan=1 colspan=1>Stores all system information</td></tr></table>

At this stage, all entities related to the business environment are listed without applying business logic refinement.

## b. Perform Refinement

After over-specification, refinement is performed to remove unnecessary or internal entities and combine similar entities according to system business logic.

## 3.1 Refined External Entities

<table><tr><td rowspan=1 colspan=1>Final External Entity</td><td rowspan=1 colspan=1>Justification</td></tr><tr><td rowspan=1 colspan=1>Customer</td><td rowspan=1 colspan=1>Main external user interacting with the system</td></tr><tr><td rowspan=1 colspan=1>Guest User</td><td rowspan=1 colspan=1>External visitor who browses products</td></tr><tr><td rowspan=1 colspan=1>Admin</td><td rowspan=1 colspan=1>External system controller and manager</td></tr><tr><td rowspan=1 colspan=1>Courier Service</td><td rowspan=1 colspan=1>External delivery organization</td></tr><tr><td rowspan=1 colspan=1>WhatsApp/SMS API</td><td rowspan=1 colspan=1>External notification provider</td></tr><tr><td rowspan=1 colspan=1>Email Service</td><td rowspan=1 colspan=1>External communication service</td></tr><tr><td rowspan=1 colspan=1>Payment Method (COD)</td><td rowspan=1 colspan=1>External payment handling process</td></tr></table>

## 3.2 Removed / Merged Entities During Refinement

<table><tr><td rowspan=1 colspan=1>Removed Entity</td><td rowspan=1 colspan=1>Reason</td></tr><tr><td rowspan=1 colspan=1>Inventory Staff</td><td rowspan=1 colspan=1>Considered part of Admin operations</td></tr><tr><td rowspan=1 colspan=1>Marketing Team</td><td rowspan=1 colspan=1>Managed internally through Admin Dashboard</td></tr><tr><td rowspan=1 colspan=1>Review System</td><td rowspan=1 colspan=1>Internal module of the system</td></tr><tr><td rowspan=1 colspan=1>Database</td><td rowspan=1 colspan=1>Internal component, not an external entity</td></tr><tr><td rowspan=1 colspan=1>SMS Service</td><td rowspan=1 colspan=1>Combined with WhatsApp/SMS API</td></tr></table>

## 3.2.1 Context Level Data Flow Diagram

The Context Level Data Flow Diagram (DFD) represents the complete Deen Craft E-Commerce System as a single process identified with Process 0. The diagram shows the interaction between the system and external entities along with the major data flows exchanged between them.

The context diagram does not include internal processes or data stores because it only provides a high-level overview of the system.

## External Entities

The following external entities interact with the Deen Craft E-Commerce System:

1. Customer

2. Guest User

3. Admin

4. Courier Service

5. WhatsApp/SMS API

6. Email Service

7. Payment Method (Cash on Delivery)

## Major Data Flows

<table><tr><td colspan="1" rowspan="1">External Entity</td><td colspan="1" rowspan="1">Data Sent to System</td><td colspan="1" rowspan="1">Data Received from System</td></tr><tr><td colspan="1" rowspan="1">Customer</td><td colspan="1" rowspan="1">Registration data, login details, orders,customization details, reviews</td><td colspan="1" rowspan="1">Order confirmation, trackingdetails, notifications</td></tr><tr><td colspan="1" rowspan="1">Guest User</td><td colspan="1" rowspan="1">Product search and browsing requests</td><td colspan="1" rowspan="1">Product information</td></tr><tr><td colspan="1" rowspan="1">Admin</td><td colspan="1" rowspan="1">Product details, inventory updates,order management data</td><td colspan="1" rowspan="1">Reports, analytics, alerts</td></tr><tr><td colspan="1" rowspan="1">Courier Service</td><td colspan="1" rowspan="1">Delivery status updates</td><td colspan="1" rowspan="1">Shipment details</td></tr><tr><td colspan="1" rowspan="1">WhatsApp/SMSAPI</td><td colspan="1" rowspan="1">Notification delivery status</td><td colspan="1" rowspan="1">OTPs, order notifications</td></tr><tr><td colspan="1" rowspan="1">Email Service</td><td colspan="1" rowspan="1">Email delivery status</td><td colspan="1" rowspan="1">Verification and order emails</td></tr><tr><td colspan="1" rowspan="1">Payment Method(COD)</td><td colspan="1" rowspan="1">Payment confirmation</td><td colspan="1" rowspan="1">Order payment request</td></tr></table>

## 4. DFD Diagram

![](images/3d70d928ab2a51e972b4a680463fa3f657efc43f0f8a649f59a2972411b3a8d8.jpg)

![](images/f23b8260d6051cc373f72d36fc7b636db5fb638906fecc56f70c28d3c701fc20.jpg)

## 5. Requirements:

## 5.1 Functional:

5.1.1: Authorization & User

<table><tr><td colspan="1" rowspan="1">ReqNumber</td><td colspan="1" rowspan="1">Requirement Description</td></tr><tr><td colspan="1" rowspan="1">FR-1.1</td><td colspan="1" rowspan="1">The system shall require new users to sign up using either a valid mobilenumber (with SMS verification) or an email address (with email verification).</td></tr><tr><td colspan="1" rowspan="1">FR-1.2</td><td colspan="1" rowspan="1">The system shall require user passwords to meet standard complexityrequirements (minimum 8 characters, including 1 uppercase letter and 1number).</td></tr><tr><td colspan="1" rowspan="1">FR-1.3</td><td colspan="1" rowspan="1">The system shall reject duplicate registrations for already verifiedemails/numbers.</td></tr><tr><td colspan="1" rowspan="1">FR-2.1</td><td colspan="1" rowspan="1">The system shall allow registered users to log into the web applicationusing their registered email/mobile number and password.</td></tr><tr><td colspan="1" rowspan="1">FR-2.2</td><td colspan="1" rowspan="1">The authentication session shall persist via secure HTTP-only cookies untilthe user manually logs out or the session expires.</td></tr><tr><td colspan="1" rowspan="1">FR-2.3</td><td colspan="1" rowspan="1">The system shall show a error message that “INVALID EMAIL/MOBILENUMBER OR PASSWORD” if credentials do not match.</td></tr><tr><td colspan="1" rowspan="1">FR-2.4</td><td colspan="1" rowspan="1">The system shall display a temporary block message after 5 consecutivefailed login attempts.</td></tr><tr><td colspan="1" rowspan="1">FR-2.5</td><td colspan="1" rowspan="1">After 5 consecutive failed login attempts, the system shall restrict loginaccess for exactly 15 minutes.</td></tr><tr><td colspan="1" rowspan="1">FR-2.6</td><td colspan="1" rowspan="1">The system shall allow users to request a password reset via a 6-digit OTP.</td></tr><tr><td colspan="1" rowspan="1">FR-2.7</td><td colspan="1" rowspan="1">The system shall enforce a 10-minute validity period for the password resetOTP.</td></tr><tr><td colspan="1" rowspan="1">FR-2.8</td><td colspan="1" rowspan="1">The system shall allow OTP resend only after a 60-second cooldown period.</td></tr><tr><td colspan="1" rowspan="1">FR-2.9</td><td colspan="1" rowspan="1">Upon successful OTP verification, the system shall prompt the user to enterand confirm a new password.</td></tr><tr><td colspan="1" rowspan="1">FR-2.10</td><td colspan="1" rowspan="1">Show an error message and redirect to login after 5 wrong OTP attempts.</td></tr><tr><td colspan="1" rowspan="1">FR-3.1</td><td colspan="1" rowspan="1">The system shall allow registered users to maintain a profile with theirname and contact details.</td></tr><tr><td colspan="1" rowspan="1">FR-3.2</td><td colspan="1" rowspan="1">The system shall allow registered users to save a default shipping addressin their profile.</td></tr><tr><td colspan="1" rowspan="1">FR-4</td><td colspan="1" rowspan="1">The system shall allow users to log out of their accounts by terminating theactive session.</td></tr><tr><td colspan="1" rowspan="1">FR-5.1</td><td colspan="1" rowspan="1">The system shall automatically terminate user sessions and log accountsout after 15 minutes of inactivity.</td></tr><tr><td colspan="1" rowspan="1">FR-5.2</td><td colspan="1" rowspan="1">The system shall strictly define inactivity as no client-side mousemovement, keystrokes, or active APl requests.</td></tr></table>

## 5.1.2: Catalog & Custom

<table><tr><td colspan="1" rowspan="1">FR-6</td><td colspan="1" rowspan="1">The system shall allow users to browse the product catalog as a Guest.</td></tr><tr><td colspan="1" rowspan="1">FR-7.1</td><td colspan="1" rowspan="1">The system shall categorize products based on their specific type.</td></tr><tr><td colspan="1" rowspan="1">FR-7.2</td><td colspan="1" rowspan="1">The system shall support main product categories and filtering for: Prayer Mats,Tasbeeh, Digital Counters, etc.</td></tr><tr><td colspan="1" rowspan="1">FR-8</td><td colspan="1" rowspan="1">The system shall allow users to search for products in search bar by usingkeywords.</td></tr><tr><td colspan="1" rowspan="1">FR-9</td><td colspan="1" rowspan="1">The system shall display product details including the pricing, type, quality, andusage.</td></tr><tr><td colspan="1" rowspan="1">FR-10.1</td><td colspan="1" rowspan="1">The system shall display a visible 24x24 pixel icon (customizable label) onproduct images.</td></tr><tr><td colspan="1" rowspan="1">FR-10.2</td><td colspan="1" rowspan="1">Hovering over the customization icon shall display a tooltip reading "Thisproduct can be customized".</td></tr><tr><td colspan="1" rowspan="1">FR-11.1</td><td colspan="1" rowspan="1">The system shall allow users to sort products by price in ascending anddescending order.</td></tr><tr><td colspan="1" rowspan="1">FR-11.2</td><td colspan="1" rowspan="1">The system shall support filtering products based on availability status (InStock, Out of Stock, Backorder).</td></tr><tr><td colspan="1" rowspan="1">FR-11.3</td><td colspan="1" rowspan="1">The system shall allow users to apply multiple filters simultaneously.</td></tr><tr><td colspan="1" rowspan="1">FR-11.4</td><td colspan="1" rowspan="1">The system shall rank products in “Popular Products” sections using acomposite score.</td></tr><tr><td>FR- 11.5</td><td>The system shall allow users to sort products by newest arrivals.</td></tr><tr><td>FR- 11.6</td><td>The system shall provide a “Clear Filters” option to reset all applied filters.</td></tr><tr><td>FR- 11.7</td><td>The system shall display a message when zero product records match filters.</td></tr><tr><td>FR- 12.1</td><td>The system shall provide text input fields for customizable products.</td></tr><tr><td>FR- 12.2</td><td>The system shall display the maximum allowed character limit before customization input begins.</td></tr><tr><td>FR- 12.3</td><td>The system shall provide a live character counter during customization input.</td></tr><tr><td>FR- 12.4</td><td>The system shall validate customization input before order submission.</td></tr><tr><td>FR- 12.5</td><td>The system must notify the user with a specific validation message if criteria are unmet.</td></tr><tr><td>FR-</td><td>The system shall support customization input in both English and Urdu</td></tr><tr><td>12.6 FR-</td><td>languages. Administrators shall be able to define and update character limits for</td></tr><tr><td>13.1 FR-</td><td>customizable products. The system shall restrict users from entering text beyond the defined character</td></tr><tr><td>13.2</td><td>limit. The system shall display a warning message when 90% of the allowed</td></tr><tr><td>FR- 13.3</td><td>character limit has been reached.</td></tr><tr><td>FR- 13.4</td><td>The system shall validate character limits during input processing and order submission.</td></tr><tr><td>FR-</td><td>The system shall be able to store character limit configurations in the database.</td></tr><tr><td>13.5 FR-14</td><td>The system shall allow users to select customization options including thread</td></tr><tr><td></td><td>color, font style, product color, etc.</td></tr><tr><td>FR-</td><td>The system shall require completion of all mandatory customization fields</td></tr><tr><td>15.1</td><td>before adding to cart.</td></tr><tr><td>FR-</td><td>The system shall not allow products with incomplete customization details to</td></tr><tr><td>15.2</td><td>be added to cart.</td></tr><tr><td>FR-</td><td>The system shall display validation messages for incomplete or missing</td></tr><tr><td>15.3</td><td>customization fields.</td></tr><tr><td></td><td></td></tr><tr><td>FR-</td><td>The system shall display a summary of selected customization details before</td></tr><tr><td>15.4</td><td>adding to cart.</td></tr><tr><td>FR-</td><td>The system shall allow users to edit customization selections before final</td></tr><tr><td>15.5</td><td>confirmation.</td></tr><tr><td></td><td></td></tr><tr><td>FR-</td><td>The system shall require customer confirmation before customized products</td></tr><tr><td>15.6</td><td>are added to the shopping cart.</td></tr><tr><td></td><td></td></tr><tr><td>FR-</td><td>Administrators shall be able to mark products as customizable or non-</td></tr><tr><td></td><td></td></tr><tr><td>16.1</td><td>customizable.</td></tr><tr><td></td><td></td></tr><tr><td>FR-</td><td></td></tr><tr><td></td><td>Administrators shall be able to configure customization fields and available</td></tr><tr><td>16.2</td><td></td></tr></table>

5.1.3: Cart & Checkout
<table><tr><td colspan="1" rowspan="1">FR-17.1</td><td colspan="1" rowspan="1">The system shall restrict guest users from adding products to the shoppingcart.</td></tr><tr><td colspan="1" rowspan="1">FR-17.2</td><td colspan="1" rowspan="1">The system shall require users to register or log in before accessing cart andcheckout.</td></tr><tr><td colspan="1" rowspan="1">FR-18.1</td><td colspan="1" rowspan="1">The system shall allow users to add products to the shopping cart.</td></tr><tr><td colspan="1" rowspan="1">FR-18.2</td><td colspan="1" rowspan="1">The system shall display a confirmation message after products are added.</td></tr><tr><td colspan="1" rowspan="1">FR-18.3</td><td colspan="1" rowspan="1">The shopping cart item count shall update automatically.</td></tr><tr><td colspan="1" rowspan="1">FR-18.4</td><td colspan="1" rowspan="1">The system shall allow users to increase or decrease product quantities in thecart.</td></tr><tr><td colspan="1" rowspan="1">FR-18.5</td><td colspan="1" rowspan="1">The system shall not allow the product quantity in the cart to be less than one.</td></tr><tr><td colspan="1" rowspan="1">FR-18.6</td><td colspan="1" rowspan="1">The system shall automatically recalculate cart totals after quantity changes.</td></tr><tr><td colspan="1" rowspan="1">FR-18.7</td><td colspan="1" rowspan="1">The system shall allow users to remove products from the shopping cart.</td></tr><tr><td colspan="1" rowspan="1">FR-18.8</td><td colspan="1" rowspan="1">The system shall request confirmation before removing cart items.</td></tr><tr><td colspan="1" rowspan="1">FR-18.9</td><td colspan="1" rowspan="1">The system shall update shopping cart totals automatically after item removal.</td></tr><tr><td colspan="1" rowspan="1">FR-19.1</td><td colspan="1" rowspan="1">The system shall calculate the shopping cart subtotal using product prices andquantities.</td></tr><tr><td colspan="1" rowspan="1">FR-19.2</td><td colspan="1" rowspan="1">Shipping charges shall be calculated according to the selected deliverylocation.</td></tr><tr><td colspan="1" rowspan="1">FR-19.3</td><td colspan="1" rowspan="1">The system shall calculate and display the grand total during the cart andcheckout processes.</td></tr><tr><td colspan="1" rowspan="1">FR-19.4</td><td colspan="1" rowspan="1">All product prices and totals shall be displayed in PKR currency.</td></tr><tr><td colspan="1" rowspan="1">FR-20.1</td><td colspan="1" rowspan="1">The system shall support Cash on Delivery (COD) as the available paymentmethod.</td></tr><tr><td colspan="1" rowspan="1">FR-20.2</td><td colspan="1" rowspan="1">The system shall display COD as the default selected payment option duringcheckout.</td></tr><tr><td colspan="1" rowspan="1">FR-21.1</td><td colspan="1" rowspan="1">The system shall require users to provide shipping and contact information.</td></tr><tr><td colspan="1" rowspan="1">FR-21.2</td><td colspan="1" rowspan="1">The system shall require users to enter full name before proceeding toconfirmation.</td></tr><tr><td colspan="1" rowspan="1">FR-21.3</td><td colspan="1" rowspan="1">The system shall require users to enter a valid mobile number for deliverycommunication.</td></tr><tr><td colspan="1" rowspan="1">FR-21.4</td><td colspan="1" rowspan="1">The system shall require users to enter complete delivery address includingcity and area details.</td></tr><tr><td colspan="1" rowspan="1">FR-21.5</td><td colspan="1" rowspan="1">If any mandatory shipping field is empty, the system shall display an errormessage.</td></tr><tr><td colspan="1" rowspan="1">FR-22.1</td><td colspan="1" rowspan="1">The system shall allow users to apply promotional codes during checkout.</td></tr><tr><td colspan="1" rowspan="1">FR-22.2</td><td colspan="1" rowspan="1">The system shall validate the entered promotional code before applyingdiscount.</td></tr><tr><td colspan="1" rowspan="1">FR-22.3</td><td colspan="1" rowspan="1">If valid, the system shall automatically apply the discount on total payableamount.</td></tr><tr><td colspan="1" rowspan="1">FR-22.4</td><td colspan="1" rowspan="1">If invalid/expired, the system shall display an error message.</td></tr><tr><td colspan="1" rowspan="1">FR-22.5</td><td colspan="1" rowspan="1">If validation fails, the system shall continue checkout process without applyingdiscount.</td></tr><tr><td colspan="1" rowspan="1">FR-23.1</td><td colspan="1" rowspan="1">The system shall display an order review page before final order confirmation.</td></tr><tr><td colspan="1" rowspan="1">FR-23.2</td><td colspan="1" rowspan="1">The system shall display selected product details on order review page.</td></tr><tr><td colspan="1" rowspan="1">FR-23.3</td><td colspan="1" rowspan="1">The system shall display product quantity and total payable amount on reviewpage.</td></tr><tr><td colspan="1" rowspan="1">FR-23.4</td><td colspan="1" rowspan="1">The system shall display customization details entered by customer beforeconfirmation.</td></tr><tr><td colspan="1" rowspan="1">FR-23.5</td><td colspan="1" rowspan="1">The system shall display shipping and contact details on review page.</td></tr></table>

## 5.1.4: Order Management

<table><tr><td colspan="1" rowspan="1">FR-24</td><td colspan="1" rowspan="1">The system shall allow users to view their past and current order history withfull details.</td></tr><tr><td colspan="1" rowspan="1">FR-25.1</td><td colspan="1" rowspan="1">The system shall provide a public "Track Order" page (Tracking ID + Mobilenumber).</td></tr><tr><td colspan="1" rowspan="1">FR-25.2</td><td colspan="1" rowspan="1">The system shall automatically assign “PENDING” status when an order issuccessfully placed.</td></tr><tr><td colspan="1" rowspan="1">FR-25.3</td><td colspan="1" rowspan="1">The system shall automatically update order status to “Confirmed” aftervalidation.</td></tr><tr><td colspan="1" rowspan="1">FR-25.4</td><td colspan="1" rowspan="1">The system shall automatically update order status to “PROCESSING” whenprep begins.</td></tr><tr><td colspan="1" rowspan="1">FR-25.5</td><td colspan="1" rowspan="1">The system shall automatically update order status to “DISPATCHED”whenshipment is completed.</td></tr><tr><td colspan="1" rowspan="1">FR-25.6</td><td colspan="1" rowspan="1">The system shall automatically update order status to “DELIVERED” aftersuccessful delivery.</td></tr><tr><td colspan="1" rowspan="1">FR-25.7</td><td colspan="1" rowspan="1">If the user enters an invalid tracking ID, the system shall display an errormessage. (incorrect tracking ID)</td></tr><tr><td colspan="1" rowspan="1">FR-25.8</td><td colspan="1" rowspan="1">The system shall display estimated delivery date ranges in the order trackingpage.</td></tr><tr><td colspan="1" rowspan="1">FR-26.1</td><td colspan="1" rowspan="1">The system shall allow full order cancellation by selecting a reason viapredefined dropdown.</td></tr><tr><td colspan="1" rowspan="1">FR-26.2</td><td colspan="1" rowspan="1">The system shall allow order cancellation when order status is “PENDING”.</td></tr><tr><td colspan="1" rowspan="1">FR-26.3</td><td colspan="1" rowspan="1">The system shall allow order cancellation when order status is “PROCESSING”.</td></tr><tr><td colspan="1" rowspan="1">FR-26.4</td><td colspan="1" rowspan="1">If order status changes to “DISPATCHED”, the system shall restrict ordercancellation.</td></tr><tr><td colspan="1" rowspan="1">FR-26.5</td><td colspan="1" rowspan="1">Display an error message if customer attempts cancellation after dispatch.</td></tr><tr><td colspan="1" rowspan="1">FR-27.1</td><td colspan="1" rowspan="1">The system shall hide the cancellation button when the order status is"Dispatched" or later.</td></tr><tr><td colspan="1" rowspan="1">FR-27.2</td><td colspan="1" rowspan="1">The system shall allow order cancellation only when status is “Pending”,“Confirmed”, or“Processing”.</td></tr><tr><td colspan="1" rowspan="1">FR-28</td><td colspan="1" rowspan="1">The system shall allow the Admin to view all customer orders.</td></tr><tr><td colspan="1" rowspan="1">FR-29</td><td colspan="1" rowspan="1">The system shall allow order filtering by status, date, customer, or Order ID.</td></tr><tr><td colspan="1" rowspan="1">FR-30</td><td colspan="1" rowspan="1">The system shall allow Admins to manually transition order statuses strictly bylifecycle.</td></tr><tr><td colspan="1" rowspan="1">FR-31</td><td colspan="1" rowspan="1">The system shall display customer customization details inside order details.</td></tr></table>

## 5.1.5: Inventory

<table><tr><td colspan="1" rowspan="1">FR-32.1</td><td colspan="1" rowspan="1">The system shall maintain and track total stock quantity for every product.</td></tr><tr><td colspan="1" rowspan="1">FR-32.2</td><td colspan="1" rowspan="1">The system shall calculate Available_Stock as Total_Stock minusReserved_Stock.</td></tr><tr><td colspan="1" rowspan="1">FR-32.3</td><td colspan="1" rowspan="1">The system shall display "In Stock" (Green) when Available_Stock is greaterthan Reorder_Level.</td></tr><tr><td colspan="1" rowspan="1">FR-32.4</td><td colspan="1" rowspan="1">The system shall display "Low Stock" (Yellow) when Available_Stock is greaterthan 0 but less than or equal to Reorder_Level.</td></tr><tr><td colspan="1" rowspan="1">FR-32.5</td><td colspan="1" rowspan="1">The system shall display "Out of Stock" (Red) when Available_Stock equals 0.</td></tr><tr><td colspan="1" rowspan="1">FR-32.6</td><td colspan="1" rowspan="1">The system shall allow Admin to view exact values for Total_Stock,Reserved_Stock, and Available_Stock.</td></tr><tr><td colspan="1" rowspan="1">FR-32.7</td><td colspan="1" rowspan="1">The system shall ensure that Total_Stock is always greater than or equal toReserved_Stock.</td></tr><tr><td colspan="1" rowspan="1">FR-32.8</td><td colspan="1" rowspan="1">The system shall alert Admin if negative stock is detected.</td></tr><tr><td colspan="1" rowspan="1">FR-33.1</td><td colspan="1" rowspan="1">The system shall deduct purchased quantity from inventory when the orderstatus changes to "Confirmed" if stock is available.</td></tr><tr><td colspan="1" rowspan="1">FR-33.2</td><td colspan="1" rowspan="1">The system shall not deduct stock when the order status is “Pending” and shalldeduct stock when "Confirmed" for COD.</td></tr><tr><td colspan="1" rowspan="1">FR-33.3</td><td colspan="1" rowspan="1">The system shall automatically recalculate Available_Stock after stockdeduction.</td></tr><tr><td colspan="1" rowspan="1">FR-33.4</td><td colspan="1" rowspan="1">The system shall verify that Available_Stock is greater than or equal toQuantity_Requested before deduction.</td></tr><tr><td colspan="1" rowspan="1">FR-33.5</td><td colspan="1" rowspan="1">The system shall not deduct stock when Available_Stock is insufficient andretain order as “Pending (Awaiting Stock)”.</td></tr><tr><td colspan="1" rowspan="1">FR-34.1</td><td colspan="1" rowspan="1">The system shall allow customers to place orders for out-of-stock productswhen Available_Stock equals 0.</td></tr><tr><td colspan="1" rowspan="1">FR-34.2</td><td colspan="1" rowspan="1">The system shall allow customers to add out-of-stock products to the cart andproceed to checkout.</td></tr><tr><td colspan="1" rowspan="1">FR-34.3</td><td colspan="1" rowspan="1">The system shall display the warning: "This product is currently out of stock. Wewill fulfill your order as soon as stock arrives."</td></tr><tr><td colspan="1" rowspan="1">FR-34.4</td><td colspan="1" rowspan="1">The system shall set the order status to "Pending (Awaiting Stock)" for out-of-stock orders.</td></tr><tr><td colspan="1" rowspan="1">FR-34.5</td><td colspan="1" rowspan="1">The system shall allow customers to cancel out-of-stock orders if status is"Pending" or "Confirmed".</td></tr><tr><td colspan="1" rowspan="1">FR-35.1</td><td colspan="1" rowspan="1">The system shall trigger an alert when a customer places an order containingout-of-stock items.</td></tr><tr><td colspan="1" rowspan="1">FR-35.2</td><td colspan="1" rowspan="1">The system shall send the alert to Admin within 30 seconds through In-AppNotification, Email, and SMS/WhatsApp.</td></tr><tr><td colspan="1" rowspan="1">FR-35.3</td><td colspan="1" rowspan="1">The system shall include Order ID, Customer Name/Contact, Order Date/Time,and out-of-stock items in the alert.</td></tr><tr><td colspan="1" rowspan="1">FR-35.4</td><td colspan="1" rowspan="1">The system shall display an "Out-of-Stock Orders" section in the Admindashboard.</td></tr><tr><td colspan="1" rowspan="1">FR-35.5</td><td colspan="1" rowspan="1">The system shall allow Admin to review, manage, and resolve out-of-stockalerts.</td></tr><tr><td colspan="1" rowspan="1">FR-35.6</td><td colspan="1" rowspan="1">The system shall keep the alert visible until Admin dismisses it or the orderstatus changes to "Dispatched".</td></tr><tr><td colspan="1" rowspan="1">FR-35.7</td><td colspan="1" rowspan="1">The system shall maintain alert history for a minimum of 30 days.</td></tr><tr><td colspan="1" rowspan="1">FR-36.1</td><td colspan="1" rowspan="1">The system shall monitor inventory and trigger a low stock alert when Availablefalls below Reorder_Level.</td></tr><tr><td colspan="1" rowspan="1">FR-36.2</td><td colspan="1" rowspan="1">The system shall send low stock alerts to Admin within 2 minutes via In-App,Email, and SMS/WA.</td></tr><tr><td colspan="1" rowspan="1">FR-36.3</td><td colspan="1" rowspan="1">The system shall include Product Name, Current Stock, Reorder Level, andRecommended Order Quantity in the alert.</td></tr><tr><td colspan="1" rowspan="1">FR-36.4</td><td colspan="1" rowspan="1">The system shall send the alert only once per low stock event and reset uponrestocking.</td></tr><tr><td colspan="1" rowspan="1">FR-37.1</td><td colspan="1" rowspan="1">The system shall allow Admin to adjust stock (Add Stock, Remove Stock, SetExact Stock, Adjust Reorder Level).</td></tr><tr><td colspan="1" rowspan="1">FR-37.2</td><td colspan="1" rowspan="1">The system shall log each stock adjustment with detailed parameters (ID, Time,Before/After, Reason, etc.).</td></tr><tr><td colspan="1" rowspan="1">FR-37.3</td><td colspan="1" rowspan="1">The system shall update inventory on product pages within 2 seconds afterstock adjustment.</td></tr></table>

5.1.6: Review & Rating
<table><tr><td colspan="1" rowspan="1">FR-38.1</td><td colspan="1" rowspan="1">Only administrator-approved customer reviews shall be displayed on productpages.</td></tr><tr><td colspan="1" rowspan="1">FR-38.2</td><td colspan="1" rowspan="1">The system shall calculate and display the average product rating based onapproved reviews.</td></tr><tr><td colspan="1" rowspan="1">FR-38.3</td><td colspan="1" rowspan="1">The system shall display the total number of approved reviews for eachproduct.</td></tr><tr><td colspan="1" rowspan="1">FR-38.4</td><td colspan="1" rowspan="1">The system shall display a “Verified Purchase” label for customers who havepurchased the product.</td></tr><tr><td colspan="1" rowspan="1">FR-38.5</td><td colspan="1" rowspan="1">The system shall allow users to view review details including rating, reviewtext, date, and images.</td></tr><tr><td colspan="1" rowspan="1">FR-38.6</td><td colspan="1" rowspan="1">The system shall support review sorting by newest, oldest, and highest-ratedreviews.</td></tr><tr><td colspan="1" rowspan="1">FR-38.7</td><td colspan="1" rowspan="1">The system shall allow users to filter reviews based on star ratings from 1 to 5.</td></tr><tr><td colspan="1" rowspan="1">FR-38.8</td><td colspan="1" rowspan="1">The system shall display a message when no reviews are available for aproduct.</td></tr><tr><td colspan="1" rowspan="1">FR-38.9</td><td colspan="1" rowspan="1">The system shall allow authenticated users to mark reviews as helpful.</td></tr><tr><td colspan="1" rowspan="1">FR-38.10</td><td colspan="1" rowspan="1">The system shall allow users to report inappropriate or offensive reviews foradministrative action.</td></tr><tr><td colspan="1" rowspan="1">FR-39.1</td><td colspan="1" rowspan="1">The system shall allow customers to submit reviews strictly for products inorders with status “Delivered”.</td></tr><tr><td colspan="1" rowspan="1">FR-39.2</td><td colspan="1" rowspan="1">The system shall enforce one review per customer per product.</td></tr><tr><td colspan="1" rowspan="1">FR-39.3</td><td colspan="1" rowspan="1">The system shall require Star Rating (1–5 stars) as a mandatory field.</td></tr><tr><td colspan="1" rowspan="1">FR-39.4</td><td colspan="1" rowspan="1">The system shall require Review Text (minimum 20 and maximum 500characters) as mandatory.</td></tr><tr><td colspan="1" rowspan="1">FR-39.5</td><td colspan="1" rowspan="1">The system shall allow photo attachments as an optional field for reviews.</td></tr><tr><td colspan="1" rowspan="1">FR-39.6</td><td colspan="1" rowspan="1">The system shall enforce a maximum limit of 3 images per review.</td></tr><tr><td colspan="1" rowspan="1">FR-39.7</td><td colspan="1" rowspan="1">The system shall allow customers to edit reviews within 24 hours ofsubmission.</td></tr><tr><td colspan="1" rowspan="1">FR-39.8</td><td colspan="1" rowspan="1">The system shall allow customers to delete reviews at any time.</td></tr><tr><td colspan="1" rowspan="1">FR-40</td><td colspan="1" rowspan="1">The system shall keep newly submitted reviews in Pending status until Adminapproval.</td></tr><tr><td colspan="1" rowspan="1">FR-41</td><td colspan="1" rowspan="1">The system shall allow the Admin to approve or reject reviews.</td></tr></table>

## 5.1.7: Admin Panel

<table><tr><td colspan="1" rowspan="1">FR-42.1</td><td colspan="1" rowspan="1">The system shall allow the Admin to create new products.</td></tr><tr><td colspan="1" rowspan="1">FR-42.2</td><td colspan="1" rowspan="1">The system shall allow the Admin to add images to products.</td></tr><tr><td colspan="1" rowspan="1">FR-42.3</td><td colspan="1" rowspan="1">The system shall allow the Admin to set pricing, descriptions, and categoriesfor products.</td></tr><tr><td colspan="1" rowspan="1">FR-43.1</td><td colspan="1" rowspan="1">The system shall allow the Admin to edit existing products.</td></tr><tr><td colspan="1" rowspan="1">FR-43.2</td><td colspan="1" rowspan="1">The system shall allow the Admin to delete existing products.</td></tr><tr><td colspan="1" rowspan="1">FR-44.1</td><td colspan="1" rowspan="1">The system shall provide a dashboard with sales analytics.</td></tr><tr><td colspan="1" rowspan="1">FR-44.2</td><td colspan="1" rowspan="1">The system shall display order summaries on the admin dashboard.</td></tr><tr><td colspan="1" rowspan="1">FR-45</td><td colspan="1" rowspan="1">The system shall allow the Admin to view customer profiles and order history.</td></tr><tr><td colspan="1" rowspan="1">FR-46</td><td colspan="1" rowspan="1">The system shall allow the Admin to search products and orders usingkeywords.</td></tr><tr><td colspan="1" rowspan="1">FR-47.1</td><td colspan="1" rowspan="1">The system shall allow the Admin to create percentage-based discountcoupons.</td></tr><tr><td colspan="1" rowspan="1">FR-47.2</td><td colspan="1" rowspan="1">The system shall allow the Admin to create fixed amount discount coupons.</td></tr><tr><td colspan="1" rowspan="1">FR-48.1</td><td colspan="1" rowspan="1">The system shall allow the Admin to define coupon expiration dates.</td></tr><tr><td colspan="1" rowspan="1">FR-48.2</td><td colspan="1" rowspan="1">The system shall allow the Admin to define usage limits for coupons.</td></tr><tr><td colspan="1" rowspan="1">FR-49</td><td colspan="1" rowspan="1">The system shall allow the Admin to upload promotional banners forhomepage campaigns.</td></tr><tr><td colspan="1" rowspan="1">FR-50</td><td colspan="1" rowspan="1">The system shall allow the Admin to apply category-level promotionaldiscounts.</td></tr><tr><td colspan="1" rowspan="1">FR-51</td><td colspan="1" rowspan="1">The system shall allow the Admin to configure delivery charges.</td></tr><tr><td colspan="1" rowspan="1">FR-52</td><td colspan="1" rowspan="1">The system shall validate all mandatory user inputs and display field-specificerror text.</td></tr><tr><td colspan="1" rowspan="1">FR-53.1</td><td colspan="1" rowspan="1">The system shall allow the Admin to enable or disable Maintenance Mode.</td></tr><tr><td colspan="1" rowspan="1">FR-53.2</td><td colspan="1" rowspan="1">When Maintenance Mode is enabled, customer pages shall display amaintenance notice.</td></tr><tr><td colspan="1" rowspan="1">FR-54.1</td><td colspan="1" rowspan="1">The dashboard homepage shall display metrics including orders, inventory,reviews, and analytics.</td></tr><tr><td colspan="1" rowspan="1">FR-54.2</td><td colspan="1" rowspan="1">The admin dashboard shall support order, review, inventory, customer, andanalytics management.</td></tr><tr><td colspan="1" rowspan="1">FR-54.3</td><td colspan="1" rowspan="1">Administrators shall be able to export reports in PDF and CSV formats.</td></tr></table>

## 5.1.8: Notifications

<table><tr><td colspan="1" rowspan="1">FR-55.1</td><td colspan="1" rowspan="1">The system shall automatically send order confirmation when the order statuschanges to "Pending".</td></tr><tr><td colspan="1" rowspan="1">FR-55.2</td><td colspan="1" rowspan="1">The system shall attempt to send notifications via the WhatsApp API as theprimary channel.</td></tr><tr><td colspan="1" rowspan="1">FR-55.3</td><td colspan="1" rowspan="1">The system shall include Order ID, Total Amount, Items, Payment Method,Tracking Link, etc., in the message.</td></tr><tr><td colspan="1" rowspan="1">FR-55.4</td><td colspan="1" rowspan="1">The system shall personalize the notification using the customer's first name.</td></tr><tr><td colspan="1" rowspan="1">FR-55.5</td><td colspan="1" rowspan="1">The system shall log all notifications with Notification_ID, Delivery_Status, andRetry_Count.</td></tr><tr><td colspan="1" rowspan="1">FR-56.1</td><td colspan="1" rowspan="1">The system shall automatically send a dispatch notification when status is"Dispatched".</td></tr><tr><td colspan="1" rowspan="1">FR-56.2</td><td colspan="1" rowspan="1">The system shall attempt to send notifications via the WhatsApp APl as theprimary channel.</td></tr><tr><td colspan="1" rowspan="1">FR-56.3</td><td colspan="1" rowspan="1">The system shall include Order ID, Courier Name, Tracking Number/Link, andETA in the notification.</td></tr><tr><td colspan="1" rowspan="1">FR-56.4</td><td colspan="1" rowspan="1">The system shall wait 5 minutes after dispatch status change before sendingthe notification.</td></tr><tr><td colspan="1" rowspan="1">FR-56.5</td><td colspan="1" rowspan="1">The system shall display "Delivery by Deen Craft" with driver name for localdeliveries.</td></tr><tr><td colspan="1" rowspan="1">FR-57.1</td><td colspan="1" rowspan="1">The system shall automatically send cancellation confirmation when status is"Cancelled".</td></tr><tr><td colspan="1" rowspan="1">FR-57.2</td><td colspan="1" rowspan="1">The system shall attempt to send notifications via the WhatsApp APl as theprimary channel.</td></tr><tr><td colspan="1" rowspan="1">FR-57.3</td><td colspan="1" rowspan="1">The system shall include Original Total Amount and Cancellation Reason in thenotification.</td></tr><tr><td colspan="1" rowspan="1">FR-57.4</td><td colspan="1" rowspan="1">The system shall mention if a promo code discount was reversed.</td></tr><tr><td colspan="1" rowspan="1">FR-57.5</td><td colspan="1" rowspan="1">The system shall not send cancellation notifications if the order is blocked fromcancellation.</td></tr></table>

## 5.2 Non-Functional:

## 5.2.1 General NFRs

<table><tr><td colspan="1" rowspan="1">NFR-1</td><td colspan="1" rowspan="1">The system shall display the Deen Craft logo permanently on the top navigationbar.</td></tr><tr><td colspan="1" rowspan="1">NFR-2.1</td><td colspan="1" rowspan="1">The system shall present a user interface that utilizes standard grid-based e-commerce layouts.</td></tr><tr><td colspan="1" rowspan="1">NFR-2.2</td><td colspan="1" rowspan="1">The user interface shall strictly adhere to the project's designated brand styleguide, utilizing specified geometric background SVG patterns and the approvedcolor palette to maintain a consistent thematic brand identity across all pages.</td></tr><tr><td colspan="1" rowspan="1">NFR-4.1</td><td colspan="1" rowspan="1">The homepage and product pages must be loaded and be ready to use with amaximum time of 3 seconds on a standard 4G internet connection or wifi (atleast 15 Mbps speed).</td></tr><tr><td colspan="1" rowspan="1">NFR-4.2</td><td colspan="1" rowspan="1">If the page fails to load within 3 seconds, the system shall automatically displaya user-friendly timeout message (e.g., 'Slow connection, please refresh').</td></tr><tr><td colspan="1" rowspan="1">NFR-5.1</td><td colspan="1" rowspan="1">The system must handle at least 500 concurrent users using the website at theexact same time along with that different users performing different tasksincluding searching, placing orders, checkout process, signing in, logging out,adding to cart along with booking up of customized products.</td></tr><tr><td colspan="1" rowspan="1">NFR-5.2</td><td colspan="1" rowspan="1">While handling these 500 active users, the system must process and respond toevery user click or action within a maximum of 2 seconds.</td></tr><tr><td colspan="1" rowspan="1">NFR-5.3</td><td colspan="1" rowspan="1">If the system cannot process an action within 2 seconds due to high traffic ofmore than 500 concurrent users, then the system must immediately show a"loading" or "processing" indicator to the user.</td></tr><tr><td colspan="1" rowspan="1">NFR-5.4</td><td colspan="1" rowspan="1">If the system fails to complete the action within 10 seconds, the system mustcancel the request and display a friendly message like "Server is busy, please tryagain later" to prevent the screen from freezing.</td></tr><tr><td colspan="1" rowspan="1">NFR-6.1</td><td colspan="1" rowspan="1">The system shall support responsive layouts for mobile devices, tablets,desktops, and large desktop screens.</td></tr><tr><td colspan="1" rowspan="1">NFR-6.2</td><td colspan="1" rowspan="1">The system shall support screen widths starting from 320 pixels without layoutdistortion.</td></tr><tr><td>NFR- 6.3</td><td>All interactive elements shall maintain a minimum touch target size of 48 × 48 pixels.</td></tr><tr><td>NFR-</td><td>The system shall maintain a minimum color contrast ratio of 4.5:1 according to</td></tr><tr><td>8.1</td><td>WCAG accessibility guidelines. The user interface shall strictly adhere to the project's designated brand style</td></tr><tr><td>NFR- 8.2</td><td>guide, utilizing specified geometric background SVG patterns and the approved</td></tr><tr><td>NFR-</td><td>color palette to maintain a consistent thematic brand identity across all pages. The system shall maintain consistent color schemes and interface design</td></tr><tr><td>8.3 NFR-</td><td>across all pages. The system shall use a minimum font size of 16 pixels for body text and clear</td></tr><tr><td>8.4</td><td>typography for readability.</td></tr><tr><td>NFR-</td><td>The system shall not rely solely on color to communicate important</td></tr><tr><td>8.5</td><td>information.</td></tr><tr><td>NFR-</td><td>The system shall secure all communication between users and the website by</td></tr><tr><td>10.1</td><td>using HTTPS protocol with TLS version 1.2 or higher.</td></tr><tr><td>NFR- 10.2</td><td>The system shall encrypt customer login data, shipping information, and order details during data transmission.</td></tr><tr><td>NFR-</td><td>The system shall validate and sanitize all user inputs before processing them.</td></tr><tr><td>12.1</td><td></td></tr><tr><td>NFR- 12.2</td><td>The system shall prevent SQL Injection attacks through secure query execution and parameterized statements.</td></tr><tr><td>NFR-</td><td>The system shall prevent Cross-Site Scripting (XSS) attacks by filtering harmful</td></tr><tr><td>12.3</td><td>scripts and invalid input data.</td></tr><tr><td>NFR-</td><td>If malicious input is detected, the system shall reject the request and display an</td></tr><tr><td>12.4</td><td>error message i.e “INVALID INPUT DETECTED”.</td></tr><tr><td>NFR-</td><td>The system shall encrypt all customer Pll at rest using AES-256 encryption.</td></tr><tr><td>13.1 NFR-</td><td>The system shall not expose customer phone numbers, addresses, or email</td></tr><tr><td>13.2</td><td>addresses to unauthorized third parties</td></tr><tr><td>NFR-</td><td>The system shall maintain a minimum uptime of 99.9%, allowing a maximum</td></tr><tr><td>14.1</td><td>downtime of 43 minutes per month.</td></tr><tr><td>NFR-</td><td>The system shall implement load balancing across 2 servers to distribute traffic</td></tr><tr><td>14.2</td><td>during peak load conditions.</td></tr><tr><td>NFR-</td><td>The system shall maintain standby failover instances that can take over system</td></tr><tr><td>14.3</td><td>operations within 5 minutes in case of primary server failure.</td></tr><tr><td>NFR-</td><td>The system shall perform automated daily backups of the database at 2:00 AM</td></tr><tr><td>15.1</td><td>UTC.</td></tr><tr><td>NFR-</td><td>The system shall include all database tables including orders, users, products,</td></tr><tr><td>15.2</td><td>reviews, inventory, and audit logs in daily backups.</td></tr><tr><td>NFR-</td><td>The system shall retain a minimum of 30 days of daily backup snapshots.</td></tr><tr><td></td><td></td></tr><tr><td>15.3</td><td></td></tr><tr><td>NFR-</td><td>The system shall store the encrypted backup snapshot in a secure,</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td>15.4</td><td></td></tr><tr><td></td><td>geographically isolated cloud storage bucket (e.g., AWS S3).</td></tr><tr><td>NFR-</td><td>The SRE or System Admin shall perform a quarterly restoration test.</td></tr><tr><td colspan="1" rowspan="1">NFR-16.1</td><td colspan="1" rowspan="1">The system shall create hourly database snapshots capturing the completedatabase state.</td></tr><tr><td colspan="1" rowspan="1">NFR-16.2</td><td colspan="1" rowspan="1">The system shall recover to the state of the last hourly snapshot in the event ofserver failure with a maximum of 1 hour data loss.</td></tr><tr><td colspan="1" rowspan="1">NFR-16.3</td><td colspan="1" rowspan="1">The system shall automatically detect server failure and initiate failover tobackup instances within 5 minutes.</td></tr><tr><td colspan="1" rowspan="1">NFR-18.1</td><td colspan="1" rowspan="1">The system shall use a modular, maintainable, and well-documented codestructure to support future enhancements and integrations.</td></tr><tr><td colspan="1" rowspan="1">NFR-18.2</td><td colspan="1" rowspan="1">The system shall follow standard coding conventions and version controlpractices to support collaborative development.</td></tr><tr><td colspan="1" rowspan="1">NFR-18.3</td><td colspan="1" rowspan="1">The system architecture shall support future integrations such as onlinepayment gateways, delivery tracking APIs, and multi-admin functionality.</td></tr><tr><td colspan="1" rowspan="1">NFR-19.1</td><td colspan="1" rowspan="1">The website shall function consistently across the latest stable versions ofmajor web browsers including Google Chrome, Mozilla Firefox, Microsoft Edge,and Safari.</td></tr><tr><td colspan="1" rowspan="1">NFR-19.2</td><td colspan="1" rowspan="1">The frontend user interface shall be responsive and compatible with defaultmobile browsers on both Android and iOS devices.</td></tr><tr><td colspan="1" rowspan="1">NFR-19.3</td><td colspan="1" rowspan="1">The system shall maintain consistent UI/UX behavior across supported devicesand browsers.</td></tr><tr><td colspan="1" rowspan="1">NFR-20.3</td><td colspan="1" rowspan="1">The frontend shall automatically compress images to ensure they are strictlyunder 5MB per file before upload.</td></tr></table>

5.2.2: Authorization & User
<table><tr><td rowspan=1 colspan=1>NFR-10.3</td><td rowspan=1 colspan=1>If an insecure connection is detected, the system shall restrict sensitiveoperations such as login and checkout process.</td></tr><tr><td rowspan=1 colspan=1>NFR-11.1</td><td rowspan=1 colspan=1>The system shall securely hash passwords and OTP-related data beforestoring them in database.</td></tr><tr><td rowspan=1 colspan=1>NFR-11.2</td><td rowspan=1 colspan=1>The system shall use secure hashing algorithms such as BCrypt withminimum cost factor of 10 for password protection.</td></tr><tr><td rowspan=1 colspan=1>NFR-</td><td rowspan=2 colspan=1>The system shall prevent direct retrieval or visibility of original passwords fromdatabase records.</td></tr><tr><td rowspan=1 colspan=1>11.3</td></tr></table>

5.2.3: Catalog & Custom
<table><tr><td colspan="1" rowspan="1">NFR-2.3</td><td colspan="1" rowspan="1">The system shall incorporate high-resolution pictures or 1-second loopingvideo clips of prayer mats, tasbeehs, and digital counters.</td></tr><tr><td colspan="1" rowspan="1">NFR-3</td><td colspan="1" rowspan="1">The system shall automatically compress all newly uploaded product imagesto a maximum file size of 200 KB and convert them to WebP format beforesaving them to the storage.</td></tr><tr><td colspan="1" rowspan="1">NFR-6.5</td><td colspan="1" rowspan="1">Customization forms shall be optimized for mobile usability and touchinteraction.</td></tr><tr><td colspan="1" rowspan="1">NFR-20.1</td><td colspan="1" rowspan="1">The system shall display product images with a minimum 800x800 pixelresolution.</td></tr><tr><td>NFR- 20.2</td><td>The visual product mockup preview (rendering the user's selected text and color overlaid onto the product image) shall update dynamically within 2 seconds of the user modifying a customization input.</td></tr></table>

## 5.2.4: Cart & Checkout

<table><tr><td rowspan=1 colspan=1>NFR-6.4</td><td rowspan=1 colspan=1>Shopping cart and checkout pages shall remain fully responsive withouthorizontal scrolling.</td></tr><tr><td rowspan=1 colspan=1>NFR-7.1</td><td rowspan=1 colspan=1>The checkout process shall consist of a maximum of four steps.</td></tr><tr><td rowspan=1 colspan=1>NFR-7.2</td><td rowspan=1 colspan=1>The system shall display a visual progress indicator throughout the checkoutprocess.</td></tr></table>

## 5.2.5: Inventory

<table><tr><td rowspan="2">NFR- 20.4</td><td>The system shall update inventory on product pages within 2 seconds of any</td></tr><tr><td></td></tr></table>

## 5.2.6: Admin Panel

<table><tr><td rowspan=1 colspan=1>NFR-9.1</td><td rowspan=1 colspan=1>Administrative operations shall be manageable through a graphical userinterface without requiring programming knowledge.</td></tr><tr><td rowspan=1 colspan=1>NFR-9.2</td><td rowspan=1 colspan=1>The admin dashboard shall provide navigation menus and sections withdescriptive and easily understandable labels.</td></tr><tr><td rowspan=1 colspan=1>NFR-9.3</td><td rowspan=1 colspan=1>The system shall display success and error messages for all administrativeoperations.</td></tr><tr><td rowspan=1 colspan=1>NFR-22</td><td rowspan=1 colspan=1>The underlying database schema and codebase modularity must supportmultiple administrative roles for future enhancements.</td></tr></table>

## 5.2.7: Notifications

<table><tr><td rowspan=1 colspan=1>NFR-17.1</td><td rowspan=1 colspan=1>The system shall implement retry and fallback mechanisms for third-partyWhatsApp/SMS notification services in case message delivery fails.</td></tr><tr><td rowspan=1 colspan=1>NFR-17.2</td><td rowspan=1 colspan=1>The system shall log all failed notification attempts for monitoring andtroubleshooting purposes.</td></tr><tr><td rowspan=1 colspan=1>NFR-17.3</td><td rowspan=1 colspan=1>The system shall ensure notification delivery attempts do not affect the corecheckout or order placement process.</td></tr><tr><td rowspan=1 colspan=1>NFR-21.1</td><td rowspan=1 colspan=1>If the WhatsApp API returns a 4xx/5xx error or times out after 10 seconds, thesystem shall automatically trigger an SMS fallback to the user&#x27;s mobilenumber.</td></tr><tr><td rowspan=1 colspan=1>NFR-21.2</td><td rowspan=1 colspan=1>The system shall send notifications within 120 seconds with a maximum of 3retries at 30-second intervals.</td></tr><tr><td rowspan=1 colspan=1>NFR-21.3</td><td rowspan=1 colspan=1>The system shall retry failed notifications up to 3 times within 30 minutes.</td></tr></table>

## 6. Allocated Requirements:

<table><tr><td colspan="1" rowspan="1">Module</td><td colspan="1" rowspan="1">Req ID</td><td colspan="1" rowspan="1">Use Case Name</td></tr><tr><td colspan="1" rowspan="1">1: Auth &amp; User</td><td colspan="1" rowspan="1">FR-1.1 to FR-1.3</td><td colspan="1" rowspan="1">UC_User_Registration</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-2.1, FR-2.3</td><td colspan="1" rowspan="1">UC_User_Login</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-2.2</td><td colspan="1" rowspan="1">UC_Session_Management</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-2.4, FR-2.5</td><td colspan="1" rowspan="1">UC_Login_Security</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-2.6 to FR-2.10</td><td colspan="1" rowspan="1">UC_Password_Reset</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-3.1, FR-3.2</td><td colspan="1" rowspan="1">UC_Manage_Profile</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-4</td><td colspan="1" rowspan="1">UC_User_Logout</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-5.1, FR-5.2</td><td colspan="1" rowspan="1">UC_Session_Timeout</td></tr><tr><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-6, FR-7.1, FR-7.2</td><td colspan="1" rowspan="1">UC_Browse_Products</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-8</td><td colspan="1" rowspan="1">UC_Search_Products</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-9, FR-10.1, FR-10.2</td><td colspan="1" rowspan="1">UC_View_Product_Details</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-11.1 to FR-11.7</td><td colspan="1" rowspan="1">UC_Filter_Sort_Products</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-12.1 to FR-12.6</td><td colspan="1" rowspan="1">UC_Customize_Product</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-13.1, FR-13.5</td><td colspan="1" rowspan="1">UC_Manage_Customization_Rules</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-13.2, FR-13.3, FR-13.4</td><td colspan="1" rowspan="1">UC_Customize_Product</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-14, FR-15.1 to FR-15.6</td><td colspan="1" rowspan="1">UC_Customize_Product</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-16.1, FR-16.2</td><td colspan="1" rowspan="1">UC_Manage_Products</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">NFR-6.5</td><td colspan="1" rowspan="1">UC_Responsive_Design</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">NFR-20.2</td><td colspan="1" rowspan="1">UC_Performance_Optimization</td></tr><tr><td colspan="1" rowspan="1">3: Cart &amp;Checkout</td><td colspan="1" rowspan="1">FR-17.1, FR-18.1 to FR-18.5,FR-18.7, FR-18.8</td><td colspan="1" rowspan="1">UC_Manage_Cart</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-17.2</td><td colspan="1" rowspan="1">UC_Guest_Checkout_Restriction</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-18.6, FR-18.9, FR-19.1 toFR-19.4</td><td colspan="1" rowspan="1">UC_Calculate_Totals</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-20.1, FR-20.2</td><td colspan="1" rowspan="1">UC_Process_Payment</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-21.1 to FR-21.5, FR-65.1,FR-65.2</td><td colspan="1" rowspan="1">UC_Checkout</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-22.1 to FR-22.5</td><td colspan="1" rowspan="1">UC_Apply_Promo_Code</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-23.1 to FR-23.5</td><td colspan="1" rowspan="1">UC_Order_Review</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">NFR-6.4</td><td colspan="1" rowspan="1">UC_Responsive_Design</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">NFR-7.1, NFR-7.2</td><td colspan="1" rowspan="1">UC_UX_Workflow</td></tr><tr><td colspan="1" rowspan="1">4: Order Mgmt</td><td colspan="1" rowspan="1">FR-24</td><td colspan="1" rowspan="1">UC_View_Order_History</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-25.1, FR-25.7, FR-25.8</td><td colspan="1" rowspan="1">UC_Track_Order</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-25.2 to FR-25.6, FR-30</td><td colspan="1" rowspan="1">UC_Manage_Order_Lifecycle</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-26.1 to FR-26.5, FR-27.1,FR-27.2</td><td colspan="1" rowspan="1">UC_Cancel_Order</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-28, FR-29</td><td colspan="1" rowspan="1">UC_Manage_Orders</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-31</td><td colspan="1" rowspan="1">UC_View_Order_Details</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-62</td><td colspan="1" rowspan="1">UC_System_Audit</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-63.1, FR-63.2</td><td colspan="1" rowspan="1">UC_Export_Data</td></tr><tr><td colspan="1" rowspan="1">5: Inventory</td><td colspan="1" rowspan="1">FR-32.1 to FR-32.7</td><td colspan="1" rowspan="1">UC_Track_Inventory</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-32.8, FR-35.1 to FR-35.3,FR-35.5, FR-35.6, FR-36.1 toFR-36.4</td><td colspan="1" rowspan="1">UC_Inventory_Alerts</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-33.1 to FR-33.4, FR-37.3</td><td colspan="1" rowspan="1">UC_Update_Inventory</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-33.5</td><td colspan="1" rowspan="1">UC_Handle_Backorders</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-34.1</td><td colspan="1" rowspan="1">UC_Place_Order</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-34.2</td><td colspan="1" rowspan="1">UC_Manage_Cart</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-34.3</td><td colspan="1" rowspan="1">UC_View_Product_Details</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-34.4</td><td colspan="1" rowspan="1">UC_Manage_Order_Lifecycle</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-34.5</td><td colspan="1" rowspan="1">UC_Cancel_Order</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-35.4</td><td colspan="1" rowspan="1">UC_View_Dashboard</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-35.7, FR-37.2</td><td colspan="1" rowspan="1">UC_System_Audit</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-37.1</td><td colspan="1" rowspan="1">UC_Manage_Inventory</td></tr><tr><td colspan="1" rowspan="1">6: Review &amp;Rating</td><td colspan="1" rowspan="1">FR-38.1 to FR-38.8</td><td colspan="1" rowspan="1">UC_View_Reviews</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-38.9, FR-38.10</td><td colspan="1" rowspan="1">UC_Interact_Reviews</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-39.1 to FR-39.8</td><td colspan="1" rowspan="1">UC_Submit_Review</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-40, FR-41</td><td colspan="1" rowspan="1">UC_Moderate_Reviews</td></tr><tr><td colspan="1" rowspan="1">7: Admin Panel</td><td colspan="1" rowspan="1">FR-42.1 to FR-43.2, FR-47.1 toFR-48.2, FR-50</td><td colspan="1" rowspan="1">UC_Manage_Products /Promotions</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-44.1, FR-44.2, FR-54.1,FR-54.2</td><td colspan="1" rowspan="1">UC_View_Dashboard</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-45, FR-46</td><td colspan="1" rowspan="1">UC_Manage_Customers /Admin_Search</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-49, FR-51, FR-53.1, FR-53.2</td><td colspan="1" rowspan="1">UC_UI_Content / Configure_Settings</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-52</td><td colspan="1" rowspan="1">UC_Input_Validation</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-54.3</td><td colspan="1" rowspan="1">UC_Export_Data</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">NFR-9.1 to NFR-9.3</td><td colspan="1" rowspan="1">UC_Admin_Usability</td></tr><tr><td colspan="1" rowspan="1">8: Notifications</td><td colspan="1" rowspan="1">FR-55.1 to FR-55.4, FR-56.1 toFR-56.5, FR-57.1 to FR-57.5</td><td colspan="1" rowspan="1">UC_Send_Notifications</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">FR-55.5, NFR-17.2</td><td colspan="1" rowspan="1">UC_System_Audit</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">NFR-17.1, NFR-17.3, NFR-21.1 to NFR-21.3</td><td colspan="1" rowspan="1">UC_API_Resilience</td></tr></table>

## 7. Priorities Requirements: -

<table><tr><td colspan="1" rowspan="1">Rank</td><td colspan="1" rowspan="1">Module</td><td colspan="1" rowspan="1">Req ID (New)</td><td colspan="1" rowspan="1">Category</td></tr><tr><td colspan="1" rowspan="1">1.0(Highest)</td><td colspan="1" rowspan="1">1: Auth &amp; User</td><td colspan="1" rowspan="1">FR-1.1, FR-1.2, FR-1.3, FR-2.1, FR-2.2, FR-2.3</td><td colspan="1" rowspan="1">Core Authentication</td></tr><tr><td colspan="1" rowspan="1">● 1.0(Highest)</td><td colspan="1" rowspan="1">1: Auth &amp; User</td><td colspan="1" rowspan="1">FR-2.4, FR-2.5</td><td colspan="1" rowspan="1">Security</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">1: Auth &amp; User</td><td colspan="1" rowspan="1">FR-2.6, FR-2.7, FR-2.8</td><td colspan="1" rowspan="1">Account Recovery</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">1: Auth &amp; User</td><td colspan="1" rowspan="1">FR-2.9, FR-2.10</td><td colspan="1" rowspan="1">Security</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">1: Auth &amp; User</td><td colspan="1" rowspan="1">FR-4</td><td colspan="1" rowspan="1">Core Authentication</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-7.1, FR-7.2</td><td colspan="1" rowspan="1">Catalog Organization</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-9</td><td colspan="1" rowspan="1">Product Information</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-12.1, FR-12.2, FR-12.3</td><td colspan="1" rowspan="1">Customization Input</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-12.4, FR-12.5</td><td colspan="1" rowspan="1">CustomizationValidation</td></tr><tr><td colspan="1" rowspan="1">● 1.0(Highest)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-12.6</td><td colspan="1" rowspan="1">Localization Support</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-13.1, FR-13.2</td><td colspan="1" rowspan="1">Character LimitEnforcement</td></tr><tr><td colspan="1" rowspan="1">● 1.0(Highest)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-13.4</td><td colspan="1" rowspan="1">CustomizationValidation</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-14</td><td colspan="1" rowspan="1">Customization Options</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-15.1 to FR-15.3</td><td colspan="1" rowspan="1">Pre-Cart Validation</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-15.4, FR-15.5, FR-15.6</td><td colspan="1" rowspan="1">CustomizationReview/Confirm</td></tr><tr><td colspan="1" rowspan="1">● 1.0(Highest)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-16.1, FR-16.2</td><td colspan="1" rowspan="1">Admin CustomizationSetup</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">3: Cart &amp;Checkout</td><td colspan="1" rowspan="1">FR-17.1, FR-17.2</td><td colspan="1" rowspan="1">Cart Access</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">3: Cart &amp;Checkout</td><td colspan="1" rowspan="1">FR-18.1 to FR-18.9</td><td colspan="1" rowspan="1">Shopping CartManagement</td></tr><tr><td colspan="1" rowspan="1">● 1.0(Highest)</td><td colspan="1" rowspan="1">3: Cart &amp;Checkout</td><td colspan="1" rowspan="1">FR-19.1 to FR-19.4</td><td colspan="1" rowspan="1">Cart Calculations</td></tr><tr><td colspan="1" rowspan="1">● 1.0(Highest)</td><td colspan="1" rowspan="1">3: Cart &amp;Checkout</td><td colspan="1" rowspan="1">FR-20.1, FR-20.2</td><td colspan="1" rowspan="1">Payment Operations</td></tr><tr><td colspan="1" rowspan="1">● 1.0(Highest)</td><td colspan="1" rowspan="1">3: Cart &amp;Checkout</td><td colspan="1" rowspan="1">FR-21.1 to FR-21.5</td><td colspan="1" rowspan="1">Shipping Validation</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">3: Cart &amp;Checkout</td><td colspan="1" rowspan="1">FR-23.1 to FR-23.5</td><td colspan="1" rowspan="1">Checkout Review</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">4: Order Mgmt</td><td colspan="1" rowspan="1">FR-25.2 to FR-25.6</td><td colspan="1" rowspan="1">Lifecycle StatusAutomation</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">4: Order Mgmt</td><td colspan="1" rowspan="1">FR-28, FR-30, FR-31</td><td colspan="1" rowspan="1">Admin OrderManagement</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">5: Inventory</td><td colspan="1" rowspan="1">FR-32.1, FR-32.2, FR-32.5,FR-32.6, FR-32.7, FR-32.8</td><td colspan="1" rowspan="1">Core Stock Tracking</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">5: Inventory</td><td colspan="1" rowspan="1">FR-33.1 to FR-33.4</td><td colspan="1" rowspan="1">Core Stock Deduction</td></tr><tr><td colspan="1" rowspan="1">● 1.0(Highest)</td><td colspan="1" rowspan="1">5: Inventory</td><td colspan="1" rowspan="1">FR-37.1, FR-37.3</td><td colspan="1" rowspan="1">Core Stock Adjustments</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">7: Admin Panel</td><td colspan="1" rowspan="1">FR-42.1, FR-42.2, FR-42.3,FR-43.1, FR-43.2</td><td colspan="1" rowspan="1">Product Management</td></tr><tr><td colspan="1" rowspan="1">●1.0(Highest)</td><td colspan="1" rowspan="1">8: Notifications</td><td colspan="1" rowspan="1">FR-55.1, FR-56.1</td><td colspan="1" rowspan="1">Core NotificationsTrigger</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">1: Auth &amp; User</td><td colspan="1" rowspan="1">FR-3.1, FR-3.2</td><td colspan="1" rowspan="1">Profile Management</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-6</td><td colspan="1" rowspan="1">Catalog Browsing</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-8</td><td colspan="1" rowspan="1">Product Search</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-10.1, FR-10.2</td><td colspan="1" rowspan="1">Visual Indicators</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-11.1 to FR-11.7</td><td colspan="1" rowspan="1">Product Filtering/Sorting</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-13.3</td><td colspan="1" rowspan="1">Customization Warning</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">2: Catalog &amp;Custom</td><td colspan="1" rowspan="1">FR-13.5</td><td colspan="1" rowspan="1">Character Limit Config</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">3: Cart &amp;Checkout</td><td colspan="1" rowspan="1">FR-22.1 to FR-22.5</td><td colspan="1" rowspan="1">Discounts &amp; Promos</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">4: Order Mgmt</td><td colspan="1" rowspan="1">FR-24</td><td colspan="1" rowspan="1">Order History</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">4: Order Mgmt</td><td colspan="1" rowspan="1">FR-25.1, FR-25.7, FR-25.8</td><td colspan="1" rowspan="1">Order Tracking UI</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">4: Order Mgmt</td><td colspan="1" rowspan="1">FR-26.1 to FR-26.5</td><td colspan="1" rowspan="1">Order Cancellation Logic</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">4: Order Mgmt</td><td colspan="1" rowspan="1">FR-27.1, FR-27.2</td><td colspan="1" rowspan="1">Cancel Button Visibility</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">4: Order Mgmt</td><td colspan="1" rowspan="1">FR-29</td><td colspan="1" rowspan="1">Order Filtering</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">5: Inventory</td><td colspan="1" rowspan="1">FR-32.3, FR-32.4</td><td colspan="1" rowspan="1">Visual Stock Indicators</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">5: Inventory</td><td colspan="1" rowspan="1">FR-33.5, FR-34.1 to FR-34.5</td><td colspan="1" rowspan="1">Backorder &amp; Out-of-Stock Handling</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">5: Inventory</td><td colspan="1" rowspan="1">FR-35.1 to FR-35.6</td><td colspan="1" rowspan="1">Out-of-Stock Alerts</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">5: Inventory</td><td colspan="1" rowspan="1">FR-36.1 to FR-36.4</td><td colspan="1" rowspan="1">Low Stock Alerts</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">6: Review &amp;Rating</td><td colspan="1" rowspan="1">FR-38.1 to FR-38.8</td><td colspan="1" rowspan="1">Display &amp; Filter Reviews</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">6: Review &amp;Rating</td><td colspan="1" rowspan="1">FR-39.1 to FR-39.8</td><td colspan="1" rowspan="1">Submit &amp; ManageReviews</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">6: Review &amp;Rating</td><td colspan="1" rowspan="1">FR-40, FR-41</td><td colspan="1" rowspan="1">Review Moderation</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">7: Admin Panel</td><td colspan="1" rowspan="1">FR-44.1, FR-44.2, FR-54.1,FR-54.2</td><td colspan="1" rowspan="1">Analytics &amp; Dashboard</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">7: Admin Panel</td><td colspan="1" rowspan="1">FR-45, FR-46</td><td colspan="1" rowspan="1">Customers &amp; Search</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">7: Admin Panel</td><td colspan="1" rowspan="1">FR-47.1, FR-47.2, FR-48.1,FR-48.2, FR-50</td><td colspan="1" rowspan="1">Promotions &amp; Coupons</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">7: Admin Panel</td><td colspan="1" rowspan="1">FR-51</td><td colspan="1" rowspan="1">Delivery Settings</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">7: Admin Panel</td><td colspan="1" rowspan="1">NFR-9.1, NFR-9.2, NFR-9.3</td><td colspan="1" rowspan="1">Admin Usability</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">8: Notifications</td><td colspan="1" rowspan="1">FR-55.2 to FR-55.4, FR-56.2to FR-56.5</td><td colspan="1" rowspan="1">Notification Details &amp;Logic</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">8: Notifications</td><td colspan="1" rowspan="1">FR-57.1 to FR-57.5</td><td colspan="1" rowspan="1">CancellationNotifications</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">8: Notifications</td><td colspan="1" rowspan="1">NFR-17.1, NFR-17.3</td><td colspan="1" rowspan="1">Notification Reliability</td></tr><tr><td colspan="1" rowspan="1">●2.0(Medium)</td><td colspan="1" rowspan="1">8: Notifications</td><td colspan="1" rowspan="1">NFR-21.1, NFR-21.2, NFR-21.3</td><td colspan="1" rowspan="1">SMS Fallback &amp; Retries</td></tr><tr><td colspan="1" rowspan="1">●3.0(Lowest)</td><td colspan="1" rowspan="1">1: Auth &amp; User</td><td colspan="1" rowspan="1">FR-5.1, FR-5.2</td><td colspan="1" rowspan="1">Session Timeout</td></tr><tr><td colspan="1" rowspan="1">●3.0(Lowest)</td><td colspan="1" rowspan="1">5: Inventory</td><td colspan="1" rowspan="1">FR-35.7, FR-37.2</td><td colspan="1" rowspan="1">Alert History &amp; Logging</td></tr><tr><td colspan="1" rowspan="1">●3.0(Lowest)</td><td colspan="1" rowspan="1">6: Review &amp;Rating</td><td colspan="1" rowspan="1">FR-38.9, FR-38.10</td><td colspan="1" rowspan="1">Review Interaction</td></tr><tr><td colspan="1" rowspan="1">●3.0(Lowest)</td><td colspan="1" rowspan="1">7: Admin Panel</td><td colspan="1" rowspan="1">FR-49</td><td colspan="1" rowspan="1">Upload Promo Banners</td></tr><tr><td colspan="1" rowspan="1">●3.0(Lowest)</td><td colspan="1" rowspan="1">7: Admin Panel</td><td colspan="1" rowspan="1">FR-52</td><td colspan="1" rowspan="1">Admin Input Validation</td></tr><tr><td colspan="1" rowspan="1">●3.0(Lowest)</td><td colspan="1" rowspan="1">7: Admin Panel</td><td colspan="1" rowspan="1">FR-53.1, FR-53.2</td><td colspan="1" rowspan="1">Maintenance Mode</td></tr><tr><td colspan="1" rowspan="1">3.0(Lowest)</td><td colspan="1" rowspan="1">7: Admin Panel</td><td colspan="1" rowspan="1">FR-54.3</td><td colspan="1" rowspan="1">Export PDF/CSV Reports</td></tr><tr><td colspan="1" rowspan="1">3.0(Lowest)</td><td colspan="1" rowspan="1">8: Notifications</td><td colspan="1" rowspan="1">FR-55.5, NFR-17.2</td><td colspan="1" rowspan="1">Logging &amp; Audits</td></tr></table>

## 8. Requirements Traceability:

## 8.1: Auth & User

<table><tr><td colspan="1" rowspan="1">Req ID (New)</td><td colspan="1" rowspan="1">Build</td><td colspan="1" rowspan="1">Use Case Name</td><td colspan="1" rowspan="1">Category</td></tr><tr><td colspan="1" rowspan="1">FR-1.1, FR-1.3</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_User_Registration</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-1.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_User_Registration</td><td colspan="1" rowspan="1">Security</td></tr><tr><td colspan="1" rowspan="1">FR-2.1</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_User_Login</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-2.3</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_User_Login</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">FR-2.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Session_Management</td><td colspan="1" rowspan="1">Security</td></tr><tr><td colspan="1" rowspan="1">FR-2.4, FR-2.5</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Login_Security</td><td colspan="1" rowspan="1">Security</td></tr><tr><td colspan="1" rowspan="1">FR-2.6, FR-2.8</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Password_Reset</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-2.7, FR-2.9, FR-2.10</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Password_Reset</td><td colspan="1" rowspan="1">Security</td></tr><tr><td colspan="1" rowspan="1">FR-3.1, FR-3.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Manage_Profile</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-4</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_User_Logout</td><td colspan="1" rowspan="1">Business / Security</td></tr><tr><td colspan="1" rowspan="1">FR-5.1</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Session_Timeout</td><td colspan="1" rowspan="1">Security</td></tr><tr><td colspan="1" rowspan="1">FR-5.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Session_Timeout</td><td colspan="1" rowspan="1">Usability</td></tr></table>

8.2: Catalog & Custom
<table><tr><td colspan="1" rowspan="1">FR-6, FR-7.1, FR-7.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Browse_Products</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-8</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Search_Products</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-9</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_View_Product_Details</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-10.1, FR-10.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_View_Product_Details</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">FR-11.1, FR-11.2, FR-11.3, FR-11.5</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Filter_Sort_Products</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-11.6, FR-11.7</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Filter_Sort_Products</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">FR-11.4</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Filter_Sort_Products</td><td colspan="1" rowspan="1">Technical</td></tr><tr><td colspan="1" rowspan="1">FR-12.1, FR-12.6, FR-14, FR-15.1, FR-15.6</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Customize_Product</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-12.2, FR-12.3, FR-12.5, FR-13.3, FR-15.3, FR-15.4, FR-15.5</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Customize_Product</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">FR-12.4, FR-13.2, FR-13.4, FR-15.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Customize_Product</td><td colspan="1" rowspan="1">Technical</td></tr><tr><td colspan="1" rowspan="1">FR-13.1</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC Manage Customization Rules</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-13.5</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Manage_Customization_Rules</td><td colspan="1" rowspan="1">Technical</td></tr><tr><td colspan="1" rowspan="1">FR-16.1, FR-16.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Manage_Products</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">NFR-6.5</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Responsive_Design</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">NFR-20.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Performance_Optimization</td><td colspan="1" rowspan="1">Performance</td></tr></table>

3: Cart & Checkout
<table><tr><td>FR-17.1, FR-18.1, FR-18.4, FR-18.7</td><td>B1</td><td>UC_Manage_Cart</td><td>Business</td></tr><tr><td colspan="1" rowspan="1">FR-18.2, FR-18.3, FR-18.8</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Manage_Cart</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">FR-18.5</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Manage_Cart</td><td colspan="1" rowspan="1">Technical</td></tr><tr><td colspan="1" rowspan="1">FR-17.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Guest_Checkout_Restriction</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-18.6, FR-18.9, FR-19.1, FR-19.2,FR-19.3, FR-19.4</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Calculate_Totals</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-20.1</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Process_Payment</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-20.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Process_Payment</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">FR-21.1, FR-21.2, FR-21.3, FR-21.4</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Checkout</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-21.5</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Checkout</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">FR-22.1, FR-22.3, FR-22.5</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Apply_Promo_Code</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-22.4</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Apply_Promo_Code</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">FR-22.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Apply_Promo_Code</td><td colspan="1" rowspan="1">Technical</td></tr><tr><td colspan="1" rowspan="1">FR-23.2, FR-23.3, FR-23.4, FR-23.5</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Order_Review</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-23.1</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Order_Review</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">NFR-6.4</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Responsive_Design</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">NFR-7.1, NFR-7.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_UX_Workflow</td><td colspan="1" rowspan="1">Usability</td></tr></table>

## 8.4: Order Mgmt

<table><tr><td rowspan=1 colspan=1>FR-24</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_View_Order_History</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-25.1, FR-25.7, FR-25.8</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Track_Order</td><td rowspan=1 colspan=1>Usability</td></tr><tr><td rowspan=1 colspan=1>FR-25.2, FR-25.3, FR-25.4, FR-25.5, FR-25.6, FR-30</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Manage_Order_Lifecycle</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-26.1, FR-26.2, FR-26.3, FR-26.4</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Cancel_Order</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-26.5, FR-27.1, FR-27.2</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Cancel_Order</td><td rowspan=1 colspan=1>Usability</td></tr><tr><td rowspan=1 colspan=1>FR-28, FR-29</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Manage_Orders</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-31</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_View_Order_Details</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-63.1, FR-63.2</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Export_Data</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-62</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_System_Audit</td><td rowspan=1 colspan=1>Technical</td></tr></table>

8.5: Inventory

<table><tr><td colspan="1" rowspan="1">FR-32.1, FR-32.6</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Track_Inventory</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-32.2, FR-32.7, FR-32.8</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Track_Inventory</td><td colspan="1" rowspan="1">Technical</td></tr><tr><td colspan="1" rowspan="1">FR-32.3, FR-32.4, FR-32.5</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Track_Inventory</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">FR-33.1, FR-33.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Update_Inventory</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-33.3, FR-33.4</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Update_Inventory</td><td colspan="1" rowspan="1">Technical</td></tr><tr><td colspan="1" rowspan="1">FR-37.3</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Update_Inventory</td><td colspan="1" rowspan="1">Performance</td></tr><tr><td colspan="1" rowspan="1">FR-33.5</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Handle_Backorders</td><td colspan="1" rowspan="1">Technical</td></tr><tr><td colspan="1" rowspan="1">FR-34.1</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Place_Order</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-34.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Manage_Cart</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-34.3</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_View_Product_Details</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">FR-34.4</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Manage_Order_Lifecycle</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-34.5</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Cancel_Order</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-35.3, FR-35.4, FR-35.5, FR-36.3</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Inventory_Alerts</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-35.6</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Inventory_Alerts</td><td colspan="1" rowspan="1">Usability</td></tr><tr><td colspan="1" rowspan="1">FR-35.1, FR-35.2, FR-36.1, FR-36.2,FR-36.4</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Inventory_Alerts</td><td colspan="1" rowspan="1">Technical</td></tr><tr><td colspan="1" rowspan="1">FR-35.4</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_View_Dashboard</td><td colspan="1" rowspan="1">Business</td></tr><tr><td colspan="1" rowspan="1">FR-35.7, FR-37.2</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_System_Audit</td><td colspan="1" rowspan="1">Technical</td></tr><tr><td colspan="1" rowspan="1">FR-37.1</td><td colspan="1" rowspan="1">B1</td><td colspan="1" rowspan="1">UC_Manage_Inventory</td><td colspan="1" rowspan="1">Business</td></tr></table>

8.6: Review & Rating
<table><tr><td rowspan=1 colspan=1>FR-38.1, FR-38.2, FR-38.3, FR-38.4, FR-38.5,FR-38.6, FR-38.7</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_View_Reviews</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-38.8</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_View_Reviews</td><td rowspan=1 colspan=1>Usability</td></tr><tr><td rowspan=1 colspan=1>FR-38.9, FR-38.10</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Interact_Reviews</td><td rowspan=1 colspan=1>Usability</td></tr><tr><td rowspan=1 colspan=1>FR-39.1, FR-39.3, FR-39.4, FR-39.5, FR-39.7,FR-39.8</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Submit_Review</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-39.2, FR-39.6</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Submit_Review</td><td rowspan=1 colspan=1>Technical</td></tr><tr><td rowspan=1 colspan=1>FR-40, FR-41</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Moderate_Reviews</td><td rowspan=1 colspan=1>Business</td></tr></table>

8.7: Admin Panel
<table><tr><td rowspan=1 colspan=1>FR-42.1, FR-42.2, FR-42.3, FR-43.1, FR-43.2</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Manage_Products</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-44.1, FR-44.2, FR-54.1, FR-54.2</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_View_Dashboard</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-45</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Manage_Customers</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-46</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Admin_Search</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-47.1, FR-47.2, FR-48.1, FR-48.2, FR-50</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Manage_Promotions</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-49</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_UI_Content</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-51</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Configure_Settings</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-53.1, FR-53.2</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Configure_Settings</td><td rowspan=1 colspan=1>Usability</td></tr><tr><td rowspan=1 colspan=1>FR-52</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Input_Validation</td><td rowspan=1 colspan=1>Technical</td></tr><tr><td rowspan=1 colspan=1>FR-54.3</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Export_Data</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>NFR-9.1, NFR-9.2, NFR-9.3</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Admin_Usability</td><td rowspan=1 colspan=1>Usability</td></tr></table>

## 8.8: Notifications

<table><tr><td rowspan=1 colspan=1>FR-55.3, FR-56.3, FR-56.5, FR-57.3, FR-57.4</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Send_Notifications</td><td rowspan=1 colspan=1>Business</td></tr><tr><td rowspan=1 colspan=1>FR-55.1, FR-55.2, FR-56.1, FR-56.2, FR-56.4,FR-57.1, FR-57.2, FR-57.5</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Send_Notifications</td><td rowspan=1 colspan=1>Technical</td></tr><tr><td rowspan=1 colspan=1>FR-55.4</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_Send_Notifications</td><td rowspan=1 colspan=1>Usability</td></tr><tr><td rowspan=1 colspan=1>FR-55.5, NFR-17.2</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_System_Audit</td><td rowspan=1 colspan=1>Technical</td></tr><tr><td rowspan=1 colspan=1>NFR-17.1, NFR-17.3, NFR-21.1, NFR-21.2,NFR-21.3</td><td rowspan=1 colspan=1>B1</td><td rowspan=1 colspan=1>UC_API_Resilience</td><td rowspan=1 colspan=1>Reliability</td></tr></table>

## 9. Use case Description& Use case Diagrams

9.1 Module 1: Authentication Module

Use Case Name : UC\_User\_Registration

Primary Actor : Guest Customer

Brief Description : A new user creates an account using a valid mobile number (with SMS verification) or an email address (with email verification). The system ensures password security and complexity during this process.

Pre-conditions : The user must not already have a verified account associated with the provided email or mobile number.

Normal Flow :

1. The user navigates to the "Sign Up" page on the website.

2. The user enters their mobile number or email address along with a password.

3. The system validates that the password meets standard complexity requirements (minimum 8 characters, including 1 uppercase letter and 1 number).

4. The system sends a One-Time Password (OTP) to verify the user's identity.

5. The user enters the OTP, and the system verifies it.

6. The system successfully creates the new account.

## Alternate/Exception Flow :

 Duplicate Registration: If the user enters an email or number that is already registered to a verified account, the system rejects the registration and displays an error message.

 Weak Password: If the password does not meet the complexity requirements, the system displays an error prompting the user to enter a stronger password.

Post-conditions : The user's record is securely saved in the database, and the user is automatically logged into their new account.

![](images/1e94d518440e682be507aefec59d404ba1db36b44cc8d7238e7cbcf5da105d20.jpg)

## 9.2 Module 2: Catalog & Customization

Use Case Name : UC\_Customize\_Product

Primary Actor : Registered User / Guest

Brief Description : The user personalizes a customizable product (such as a prayer mat or tasbeeh) by selecting options like thread color, font style, product color, and material, and by inputting custom text.

Pre-conditions : The user must be on the detail page of a product marked as "Customizable" by the Admin, which is indicated by a visible 24x24 pixel "Customizable" icon.

Normal Flow :

 The user selects the available customization options (e.g., thread color, font style) on the product page.

 The user types their custom name or text into the input field (the system supports both English and Urdu languages).

 The system displays a live character counter during input and indicates the maximum allowed limit (e.g., 15 to 20 characters).

 The user completes all mandatory customization fields.

 The system displays a summary of the selected customization details before adding the product to the shopping cart.

 The user reviews the summary and confirms their selection.

## Alternate/Exception Flow :

 Character Limit Warning & Exceeded: When the user reaches 90% of the allowed character limit, the system displays a warning message. If the user attempts to exceed the limit, the system restricts further text entry.

 Incomplete Customization: If the user attempts to add the item to the cart without filling out all mandatory customization fields, the system displays a validation error message and blocks the action.

Post-conditions : The customization details are securely attached to the specific product, and the item is added to the user's shopping cart.

![](images/66348a87d07e875942554894170a1953ee54e7b9900bbc0f52ea87a4bd86d3ed.jpg)

## 9.3 Module 3: Cart & Checkout

Use Case Name : UC\_Proceed\_to\_Checkout

Primary Actor : Registered User

Brief Description : The user reviews their shopping cart, provides shipping information, optionally applies a promotional code, and finalizes the purchase using Cash on Delivery (COD).

Pre-conditions : The user must be registered, logged into the system, and have at least one product added to their shopping cart because guest checkout is restricted.

Normal Flow :

 The user clicks on the "Proceed to Checkout" button from the shopping cart page.

 The system initiates a maximum four-step checkout process including Cart Review, Shipping Address, Payment Method, and Order Confirmation.

 The user enters their full name, valid mobile number, and complete delivery address including city and area.

 The user optionally enters a promotional code, which the system validates and applies to the grand total.

 The system automatically selects Cash on Delivery (COD) as the default payment option.

 The user reviews the final order details, including customization summaries, and clicks to place the order.

## Alternate/Exception Flow :

 Missing Shipping Details: If the user leaves any mandatory shipping field empty, the system displays an error message stating "PLEASE COMPLETE ALL REQUIRED SHIPPING DETAILS" and prevents order submission.

 Invalid Promotional Code: If the user enters an expired or invalid promotional code, the system displays an error message ("INVALID OR EXPIRED PROMOTIONAL CODE") and allows the user to continue the checkout process without the discount.

Post-conditions : The system generates a unique Order ID and Tracking ID, sets the order status to "PENDING", and sends an order confirmation notification via Email and WhatsApp/SMS.

![](images/e8d48b9d9a37fc7f55ec37cd4ccc0fabc09ec9687eeec2f63e4c27326e5b221a.jpg)

## 9.4 Module 4: Order Management

Use Case Name : UC\_Cancel\_Order

Primary Actor : Registered User

Brief Description : The user initiates a full cancellation of an active order by selecting a predefined reason, provided the order has not yet been shipped by the admin.

Pre-conditions : The user must be logged in, and the specific order must currently have a status of "Pending", "Confirmed", or "Processing".

## Normal Flow :

 The user navigates to their order history and views the details of an active order.

 The user clicks the cancellation button available on the order details page.

 The user selects a reason for cancellation from a predefined dropdown menu.

 The system processes the request and updates the order status directly to "Cancelled".

 The system automatically triggers a cancellation notification via the WhatsApp API containing the original amount and cancellation reason.

## Alternate/Exception Flow :

 Post-Dispatch Cancellation Attempt: If the order status has already changed to "Dispatched", the system hides the cancellation button. If a cancellation attempt is somehow made after dispatch, the system restricts the action and displays the error message "ORDER CANNOT BE CANCELLED AFTER DISPATCH".

Post-conditions : The order is permanently marked as cancelled in the database, and if a promo code was used, the reversal is noted in the customer notification.

![](images/956801bc40e39a721e7eca963e39f39744ed4fe8f57ab2c45fcccd35c2827055.jpg)

## 9.5 Module 5: Inventory Management

Use Case Name : UC\_Manual\_Stock\_Adjustment

Primary Actor : Admin

Brief Description : The administrator adjusts product stock levels through an interface supporting operations like Add Stock, Remove Stock, Set Exact Stock, and Adjust Reorder Level.

Pre-conditions : The Admin must be securely logged into the dashboard.

Normal Flow :

 The Admin navigates to the Inventory Management section of the dashboard.

 The Admin selects a specific product to adjust its stock.

 The Admin chooses the adjustment type (Add Stock, Remove Stock, or Set Exact Stock) and enters the values.

 The system processes the adjustment and ensures that Total\_Stock is always greater than or equal to Reserved\_Stock.

 The system logs the exact adjustment details including Adjustment\_ID, Timestamp, Product\_ID, Before/After quantities, Reason, Admin\_User\_ID, Notes, and IP\_Address.

 The system updates the inventory display on public product pages within 2 seconds.

## Alternate/Exception Flow :

 Negative Stock Detection: If the mathematical adjustment results in negative stock, the system automatically detects this and alerts the Admin.

Post-conditions : The product's Available\_Stock and Total\_Stock are updated in the database, and the action is permanently recorded in the system audit logs.

![](images/1ec869b94347263fffd4ab024c1e33d2ed93fd8c60fa9ba78fa7426fc8c5fadd.jpg)

## 9.6 Module 6: Review & Rating Module

Use Case Name : UC\_Submit\_Review

Primary Actor : Registered User (Buyer)

Brief Description : The customer submits a product review consisting of a mandatory star rating and text, along with optional photo attachments, to share their feedback.

Pre-conditions : The user must be logged into their account, and the specific product being reviewed must be part of an order with the final status of "Delivered".

## Normal Flow :

 The user accesses their order history and selects a delivered product to write a review.

 The user selects a mandatory Star Rating ranging from 1 to 5 stars.

 The user enters the mandatory Review Text, ensuring it is between the required 20 and 500 characters.

 The user optionally attaches up to a maximum of 3 images in JPG, PNG, or WebP formats.

 The user clicks to submit the review.

## Alternate/Exception Flow :

 Multiple Review Attempt: If the user attempts to submit a second review for the exact same product, the system enforces the one review per customer per product rule and blocks the submission.

 Missing Mandatory Fields: If the Star Rating or Review Text is omitted or fails the length validation, the system restricts the submission until the criteria are met.

Post-conditions : The review is successfully submitted and kept in a "Pending" status (hidden from public view) until an administrator reviews and approves it.

![](images/1437eed914b6e93256c9dca43bc4a5ba7a045d027580759caee363db69953a50.jpg)

## 9.7 Module 7: Dashboard & System Admin Module

Use Case Name : UC\_View\_Analytics\_Dashboard

Primary Actor : Admin

Brief Description : The administrator accesses a centralized dashboard to view critical business metrics, manage system operations, and export data reports in various formats.

Pre-conditions : The Admin must be successfully authenticated and securely logged into the administrative interface.

Normal Flow :

 The Admin navigates to the dashboard homepage.

 The system displays overarching business metrics, including total orders, inventory status, customer reviews, and sales analytics.

 The Admin manages specific entities such as pending orders, customer profiles, or promotional campaigns from this central interface.

 The Admin selects an option to export order reports or analytics data.

 The system successfully generates and exports the requested reports in CSV, Excel, or PDF formats.

## Alternate/Exception Flow :

 Invalid Administrative Input: If the Admin enters invalid data while configuring settings (such as delivery charges or promotional limits), the system validates the inputs before submission, rejects the action, and displays field-specific text indicating the exact reason for the error.

Post-conditions : The Admin successfully reviews the platform's analytics, and any exported reports are downloaded to the Admin's local device.

![](images/be9c8c70453e4b4d63ebecdf6733a54ead8abf764b4a771b8dca857a69822d55.jpg)

## 9.8 Module 8: Communication & Notification Engine

Use Case Name : UC\_Send\_Automated\_Notifications

Primary Actor : System

Brief Description : The system automatically formats and sends personalized notifications (such as OTPs, order confirmations, and dispatch updates) to customers primarily via the WhatsApp API, utilizing an automated SMS fallback mechanism for high reliability.

Pre-conditions : A triggering event must occur within the system (e.g., an order status changes to "Pending" or "Dispatched"), and the customer must have a valid mobile number on record.

## Normal Flow :

 The system detects a valid triggering event, such as an order status updating to "Dispatched".

 The system formats the message template, including details like tracking links or order amounts, and personalizes the notification using the customer’s first name.

 For dispatch events specifically, the system waits exactly 5 minutes after the status change to allow time for courier label generation.

 The system attempts to send the notification via the WhatsApp API as the primary communication channel.

 The system logs the notification event, recording the Channel\_Used, Delivery\_Status, and Timestamp.

## Alternate/Exception Flow :

 WhatsApp API Error & SMS Fallback: If the WhatsApp API returns a 4xx/5xx error or times out after 10 seconds, the system automatically triggers an SMS fallback to the user's mobile number to ensure the message is delivered.

 Notification Retry Protocol: The system will retry failed notification delivery attempts up to 3 times within a 30-minute window. The system ensures these background retries do not block the core checkout or order placement processes.

Post-conditions : The customer successfully receives the informational notification on their mobile device, and the final delivery status (or failure log) is permanently recorded in the system audit logs.

![](images/f6c1a105d526492cfb7c3cce5edcffcd66d92f72f88c7af420907330235618c3.jpg)

## 9.9 System diagram

![](images/338a797a8004183d89aa23d7ca401868f68301134351d07c39295f7c399e1d3b.jpg)

![](images/6906ef3d5810a0a109db2b3ecca42466487b298b53d323b3c5d1bbb0d470b1de.jpg)