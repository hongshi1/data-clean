## 1. Introduction

## Purpose

The Functional Requirements Specification will:

 Define the scope of business objectives, business functions, and organizational units covered,

Identify the business processes that the solution must facilitate,

 Facilitate a common understanding of what the functional requirements are for all parties involved,

 Establish a basis for defining the acceptance tests for the solution to confirm that what is delivered meets requirements.

In addition, this document collects and analyses ideas related to the system, forecasts how users (customers, employees, managers) will interact with it, thereby gaining a better understanding of the project scope, outlining concepts that may be developed later, and documenting ideas under consideration (which may be accepted or discarded during development).

## Overview

## a. Basic Overview:

The Cinema Management System is a comprehensive software solution for medium and large cinema complexes. The system supports both online ticket sales (web) and direct ticket sales at the counter (POS), while also providing operational management tools, reporting, and customer care.

## b. Scope Of The System:

\- Customer: Login, View movies, showtimes, trailers, Search, Book tickets online, Real-time seat selection, Pre-order food and drinks, Payment via gateway (VNPay, Momo, Visa), Receive e-tickets as QR code, Earn/redeem membership points, Cancel tickets online, Rate movies

\- Cashier (Box Office Staff): handle walk-in customers (select movie/showtime/seats), calculate total, accept cash/card payments, print physical tickets, scan QR codes for check-in, and process offline ticket cancellations at the counter. The seat map is synchronized in real- time with the online channel.

\- Cinema Manager: Full authority to manage content: movies, showtimes, screening rooms, seat maps, ticket price lists, F&B menu, and promotional programs. View revenue reports and moderate customer movie reviews.

\- System Admin: Account & permission manager (RBAC), configure system parameters (seat lock timeout, OTP, loyalty settings, API keys, etc.), monitor audit logs, unlock user accounts.

\- Concession Staff: Receive food order notifications from the Concession Display when a customer checks in, prepare combos/items, hand them over, and update the status to FULFILLED. No access to booking or payment functions.

\- External integrations: Payment gateway, email/SMS service, TMDB API for retrieving movie data.

## c. Out-of-scope Of The System:

\- Native mobile app (only responsive web supported).

\- Direct integration with cinema hardware (projectors, lighting systems) – limited to information management only.

\- Multi-language support (only Vietnamese supported, Vietnamese interface).

\- AI-based dynamic promotion system.

## Intended Audience and Reading Suggestions

This document is intended for:

 Development team: Read the entire document, especially Section 3 (Use Case Specifications) to understand business workflows and business rules; Section 2.5 (Permission Matrix) for role-based access; Section 6 (Other Requirements) for shared components.

 Documentation Team: Read Section 4 (Mockups Screen) and use cases with user interfaces such as UC07 (View Movie Details), UC14 (Receive Confirmation), UC15 (View Booking History) to write user manuals.

 UAT team: Read all of Section 3 (Use Case Specifications) – especially alternative flows (cancellation, timeout, seat locking) and business rules – to build test scenarios with real users.

## Abbreviations

<table><tr><td colspan="1" rowspan="1">Acronym</td><td colspan="1" rowspan="1">Reference</td></tr><tr><td colspan="1" rowspan="1">SRS</td><td colspan="1" rowspan="1">System Requirement Specification</td></tr><tr><td colspan="1" rowspan="1">UC</td><td colspan="1" rowspan="1">Use Case</td></tr><tr><td colspan="1" rowspan="1">BR</td><td colspan="1" rowspan="1">Business Rules</td></tr><tr><td colspan="1" rowspan="1">CBR</td><td colspan="1" rowspan="1">Common Business Rules</td></tr><tr><td colspan="1" rowspan="1">ET</td><td colspan="1" rowspan="1">Email Template</td></tr><tr><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1">Not Applicable or Not Available</td></tr><tr><td colspan="1" rowspan="1">MSG</td><td colspan="1" rowspan="1">Message</td></tr><tr><td colspan="1" rowspan="1">F&amp;B</td><td colspan="1" rowspan="1">Food and Beverage</td></tr><tr><td colspan="1" rowspan="1">JWT</td><td colspan="1" rowspan="1">JSON Web Token</td></tr><tr><td colspan="1" rowspan="1">OTP</td><td colspan="1" rowspan="1">One-Time Password</td></tr><tr><td colspan="1" rowspan="1">POS</td><td colspan="1" rowspan="1">Point of Sale</td></tr><tr><td colspan="1" rowspan="1">RBAC</td><td colspan="1" rowspan="1">Role-Based Access Control</td></tr><tr><td colspan="1" rowspan="1">TBU</td><td colspan="1" rowspan="1">To Be Updated</td></tr><tr><td colspan="1" rowspan="1">TMDB</td><td colspan="1" rowspan="1">The Movie Database</td></tr><tr><td colspan="1" rowspan="1">ui</td><td colspan="1" rowspan="1">User Interface</td></tr><tr><td colspan="1" rowspan="1">SMS</td><td colspan="1" rowspan="1">Short Message Service</td></tr><tr><td colspan="1" rowspan="1">VND</td><td colspan="1" rowspan="1">Vit Nam Đồng</td></tr><tr><td colspan="1" rowspan="1">&lt;&lt;Field&gt;&gt;</td><td colspan="1" rowspan="1">Convention for value of this field, specifically use in the context of Email Template</td></tr><tr><td colspan="1" rowspan="1">“Text Value"</td><td colspan="1" rowspan="1">Convention for mentioning a value</td></tr><tr><td colspan="1" rowspan="1">&lt;Value&gt;</td><td colspan="1" rowspan="1">Convention for mentioning special value, i.e. &lt;Today&gt;, &lt;Current User&gt;</td></tr></table>

## References

<table><tr><td rowspan=1 colspan=1>Title</td><td rowspan=1 colspan=1>Reference</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>TMDB API Documentation</td><td rowspan=1 colspan=1>https://developer.themoviedb.org/reference/intro/getting-started</td><td rowspan=1 colspan=1>External movie metadata API. Used in UC27 to auto-import movie information (title, poster, cast, director,runtime, trailer) into the system.</td></tr><tr><td rowspan=1 colspan=1>MoMo eWallet APIDocumentation</td><td rowspan=1 colspan=1>Link to the Tools, Plugins orPlatforms Website.</td><td rowspan=1 colspan=1>Payment gateway integration for MoMo e-wallet. Usedin UC13 (Process Online Payment) to handle customertransactions via QR code or deep link.</td></tr><tr><td rowspan=1 colspan=1>VNPay Merchant TechnicalDocument</td><td rowspan=1 colspan=1>https://miniai.vn/tich-hop-thanh-toan-vnpay/</td><td rowspan=1 colspan=1>Payment gateway integration for VNPay. Used in UC13(Process Online Payment) and UC23 (Process Refund) foronline card/bank transfer transactions.</td></tr><tr><td rowspan=1 colspan=1>SendGrid Email API Guide</td><td rowspan=1 colspan=1>https://docs.sendgrid.com/</td><td rowspan=1 colspan=1>Transactional email service. Used across multiple UCs forbooking confirmation, OTP, password reset, andpromotional campaign emails.</td></tr><tr><td rowspan=1 colspan=1>Twilio SMS APIDocumentation</td><td rowspan=1 colspan=1>https://www.twilio.com/docs/smş</td><td rowspan=1 colspan=1>SMS notification service. Used for OTP delivery (UC01,UC04), booking confirmation, and showtime reminders(UC14).</td></tr><tr><td rowspan=1 colspan=1>ekyc API of VNPT</td><td rowspan=1 colspan=1>https://vnptai.io/ekyc/vi</td><td rowspan=1 colspan=1>Identity Verification Service (UC40)</td></tr></table>

## 2. High Level Requirement

The primary purpose of a UML class diagram is to define the static structure of a software system. It maps out the building blocks by visualizing classes, their attributes (data), methods (behaviors), and the relationships between them.

## Class Diagram

This section shows the static relationship between each object in the system. An object could be described as an instance of a particular entity in the system. For example, “Booking Request Form” is an object in this system which holds its own information, such as: Requestor Details, Resource, Equipment, Booking Date Time…

2.1.1 Zone A: User Hierarchy  
![](images/7247a6f999637883a295f7a22fbe6c99236b02e41548b37ebc06b96df78ef8ed.jpg)  
Figure 2.1.1: Class Diagram: Zone A: User Hierarchy

2.1.2 Zone B: Cenima Infrastructure  
![](images/0d72e853f33771f3fc30cc3395b496eb9750aaee890d18e7150a7b784b5552d5.jpg)  
Figure 2.1.2: Class Diagram: Zone B: Cinema Infrastructure

## 2.1.3 Zone C: Movie

![](images/c5fced0a040dbdee021bdbde1bb173d96cb83d0e37faf13bdf24894762cabb71.jpg)

Figure 2.1.3: Class Diagram: Zone C: Movie  
2.1.4 Zone D: Showtimes And Seats Dynamic  
![](images/d514afe872dc301f4583425979b96d1023e06049dc252cb35e35f4bccaa11dcf.jpg)  
Figure 2.1.4: Class Diagram: Zone D: Showtimes And Seats Dynamic

## 2.1.5 Zone E: BOOKING PIPELINE

![](images/5544e561eadfa2a116ab33e20b8953f3e2e335b7c53c6b152c4bc395bdfc4010.jpg)  
Figure 2.1.5: Class Diagram: Zone E: BOOKING PIPELINE

2.1.6 Zone F: Pricing And Promotion  
![](images/5b928d3293d0f5d4cc9e905e30599cc29d58f26df1449d788e8968ad2fecc8b5.jpg)  
Figure 2.1.6: Class Diagram: Zone F: Pricing and Promotion

2.1.7 Zone G: Loyalty  
![](images/a45bd48feac01dc05ecdc52ab291aad089ed0bfa2192b0e09db7e3a2d4f7c256.jpg)  
Figure 2.1.7: Class Diagram: Zone G: Loyalty

2.1.8 Zone H: Review  
![](images/c0b3cdf84451c42542412bdbfef28da4e8217de9e50892c2e13be93aac88f24e.jpg)  
Figure 2.1.8: Class Diagram: Zone H: Review

## 2.1.9 Zone I: System And Admin

![](images/9660f2febf0c24a11a7b9c05a368f9d47e494021e1ba59f7a1036cecdafea1c3.jpg)  
Figure 2.1.9: Class Diagram: Zone I: System And Admin

## Workflow

This section shows the flow of tasks or steps taken by each user of the system in order to complete a business process. The user’s actions are shown in each business process stage of the system along with the conditions under which it can move to the next stage or revert to the previous.

## 2.1.10 Workflow 1: Customer Online Flow

Objective: To model the complete self-service customer journey—from selecting a movie, showtime, and seats to integrating with thirdparty payment gateways—ensuring a seamless, automated online ticket purchase that generates an E-ticket with a unique QR code while preventing double-booking

![](images/81a28bc3c50cc8af8d8a41d9b0f5d470b3638a4066acd9b14f216b27a2ccc2da.jpg)  
Figure 2.2.1: Workflow: Customer Online Flow

## 2.1.11 Workflow 2: Offline Operations Flow

Objective: To standardize the counter operations for the Cashier, covering the handling of walk-in ticket/F&B requests, processing cash or card/QR payments via external POS, and acting as the central scanning point for all QR codes (both physical and digital) to instantly sync and trigger F&B fulfilment preparation.

![](images/3dfbe026496308eb08a3317c33c6aaebae0d6cffce456258d015d0602c5b870d.jpg)  
Figure 2.2.2: Workflow: Offline Operations Flow

## 2.1.12 Workflow 3A: Cinema Manager — "Movie & Showtime Setup Workflow"

Objective: To streamline the core administrative process of setting up movie data (either manually or via TMDB API integration), scheduling showtimes across theater rooms, and configuring ticket pricing based on seat types and time slots, ensuring accurate system data before opening public sales.

![](images/464e46d98e9f2bc97a98bec7934c4d831ed1960eaba1b5a7a721bfe16b9e5dae.jpg)  
Figure 2.2.3: Workflow: Cinema Manager — "Movie & Showtime Setup Workflow"

## 2.1.13 Workflow 3B: Cinema Manager — "Business & Content Operations"

Objective: To define the independent daily management tasks of the Cinema Manager aimed at driving revenue and maintaining content quality, including creating and launching promotion campaigns via Email Service, moderating user movie reviews, and tracking real-time business analytics dashboards.

![](images/b71c2b97f24c374200af086874441725e54c0e1158acf5d8b0c9bc71e5dd6923.jpg)  
Figure 2.2.4: Workflow: Cinema Manager — "Business & Content Operations"

## 2.1.14 Workflow 4: System Admin — "Account & System Configuration Workflow"

![](images/e4d11b8d41d12cdfd26976621bb3f8783eab76bf1311f85191fb3657b5bab177.jpg)  
Figure 2.2.4: Workflow: System Admin — "Account & System Configuration Workflow"

## Context Diagram

![](images/4c188030d539e1a3dc99e147cddbe76571e909fae068b90b6619e2c991713238.jpg)  
Figure 2.3: Context Diagram

## State Transition

This represents the behavior of the system in response to user’s actions by changing state of data objects. The circle shows the state. The line that connects one state to another shows the action required for that state change to happen. These actions are usually triggered by a user.

## 2.1.15 State Transition: Booking (Online + Offline)

![](images/23a15ab2f3f896e0050d74b08b6a86cc19a931f62742ddcc65572a12ef6ce4f7.jpg)  
Figure 2.4.1: State Transition DIagram: Booking (Online + Offline)

## 2.1.16 State Transition: Refund State

![](images/f99526648ca40d2a2fad983850f48050e2748abf5a3a2f9de6290272812ec32e.jpg)  
Figure 2.4.2: State Transition DIagram: Refund State

## 2.1.17 State Transition: Seat State

![](images/2dd28bb405c27e08bc2832369ad6222a0478bf1e5425a52a8e1a8ea01147b9ad.jpg)  
Figure 2.4.3: State Transition DIagram: Seat State

## Use Case Diagram

The use case diagram here shows the specific goal and objective or how the user interacts with the system. The ellipse in the system boundary represents the system use case/functions while the stickman represents the actor/user of the system. The line connecting the actor and the use case shows that the actor can perform that function in the system to achieve a goal.

(Use UML standard for UC diagram)

## 2.1.18 Diagram Overview

![](images/b3316150379d431d655829785840ea3eb22ca92b79d77a776ec09abee38a004f.jpg)  
Figure 2.5.1: Use Case Diagram: Diagram Overview

## 2.1.19 Use Case Diagram Flow: Customer Online Flow

![](images/1e9fb660947f1cbae493e54412b251a2b04730cdcef3c0d0e776604807009384.jpg)  
Figure 2.5.2: Use Case Diagram: Customer Online Flow

## 2.1.20 Use Case Diagram Flow: Offline Operations

![](images/05c976483a066daf71100094dd4ca53724baddb6ee2c1554afa69eb370e1b1ed.jpg)  
Figure 2.5.3: Use Case Diagram: Offline Operations

## 2.1.21 Use Case Diagram Flow: Management And Admin

![](images/292e145ccdbc03f11adee1a0e013dbd9d91ae9ea28f7ec01583cc22bb3194c41.jpg)  
Figure 2.5.4: Use Case Diagram: Management And Admin

2.1.22 Actor List
<table><tr><td colspan="1" rowspan="1">#</td><td colspan="1" rowspan="1">Actor</td><td colspan="1" rowspan="1">Description</td></tr><tr><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">Guest(Primary Actor)</td><td colspan="1" rowspan="1">Unauthenticated visitor who can browse movie listings, view details, andsearch showtimes, but must register or log in to book tickets.</td></tr><tr><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">Customer(Primary Actor)</td><td colspan="1" rowspan="1">Registered and authenticated user who can book tickets online, managetheir profile, view booking history, submit reviews, and access loyalty pointfeatures.</td></tr><tr><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">Cashier(Primary Actor)</td><td colspan="1" rowspan="1">Cinema staff responsible for walk-in ticket sales via POS, QR code check-inat the entrance, and processing cancellations and refunds at the counter.</td></tr><tr><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">Cinema Manager(Primary Actor)</td><td colspan="1" rowspan="1">Senior staff who manages movie content, showtime schedules, screeningrooms, ticket pricing, promotional campaigns, and customer reviewmoderation.</td></tr><tr><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">System Admin(Primary Actor)</td><td colspan="1" rowspan="1">Highest-privilege internal user responsible for managing staff accounts androles, configuring global system settings, and viewing business reports.</td></tr><tr><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">Concession Staff</td><td colspan="1" rowspan="1">Cinema staff responsible for receiving and fulfilling food and beverage pre-</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">(Primary Actor)</td><td colspan="1" rowspan="1">orders at the concession stand, triggered upon customer check-in.</td></tr><tr><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">Email        Service        «System»(Secondary Actor)(Vendor: Sendgrid)</td><td colspan="1" rowspan="1">External notification service used to deliver OTPs, booking confirmations,QR codes, and automated showtime reminders via email and SMS.</td></tr><tr><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">SMS Service «System» (SecondaryActor)(Vendor: Twilio)</td><td colspan="1" rowspan="1">External SMS notification service (Twilio) used to deliver bookingconfirmation summaries and automated showtime reminders via SMS. OTPdelivery is handled exclusively by Email Service.</td></tr><tr><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">Payment Gateway&lt;&lt;System&gt;&gt;(Secondary Actor)</td><td colspan="1" rowspan="1">External payment processing service that handles online transactions viaVNPay, MoMo, VISA, and Mastercard.</td></tr><tr><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">Movie       Content       Provider&lt;&lt;System&gt;&gt;(Secondary Actor)</td><td colspan="1" rowspan="1">External TMDB API that provides movie metadata, poster images, andtrailers for import into the cinema system.</td></tr><tr><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">GoogleOAuthService«System»(Secondary Actor)</td><td colspan="1" rowspan="1">External authentication service enabling Google-based single sign-on for allactor types.</td></tr><tr><td colspan="1" rowspan="1">11</td><td colspan="1" rowspan="1">Identity     Verification     Service&lt;&lt;System&gt;&gt;(Secondary Actor)</td><td colspan="1" rowspan="1">External eKYC provider (VNPay eKYC / ViettelPay ID / FPT.AI) that verifiesthe authenticity of a Customer's CCCD/CMND and performs face matchingagainst a selfie photo. Used in UC-40 to validate identity documents andbiometric data.</td></tr><tr><td colspan="1" rowspan="1">12</td><td colspan="1" rowspan="1">AI Support&lt;&lt;System&gt;&gt;(Secondary Actor)</td><td colspan="1" rowspan="1">An external Al-powered conversational service integrated into the CinemaManagement System. Receives customer queries and contextual data(booking history, preferences, current catalog) from the system and returnspersonalized movie recommendations, showtime suggestions, and booking-related support responses. Operates as a stateless API service — called bythe system on behalf of the logged-in Customer, with no direct userinterface of its own.</td></tr></table>

2.1.23 Use Case List
<table><tr><td colspan="1" rowspan="1">#</td><td colspan="1" rowspan="1">UC Name</td><td colspan="1" rowspan="1">Description</td></tr><tr><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">UC-01: Register Account</td><td colspan="1" rowspan="1">Allows a Guest to create a new Customer account by providing personalinformation and verifying their identity via a 6-digit OTP sent to theirregistered email.</td></tr><tr><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">UC-02: Login</td><td colspan="1" rowspan="1">Allows any Actor to access the system using email/password credentialsor Google OAuth, and be redirected to their role-appropriate interfaceupon successful authentication.</td></tr><tr><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">UC-03: Logout</td><td colspan="1" rowspan="1">Allows any authenticated Actor to securely terminate their currentsession by invalidating the JWT token and clearing all authenticationcookies from the browser.</td></tr><tr><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">UC-04: Reset Password</td><td colspan="1" rowspan="1">Allows an Actor who has forgotten their password to verify their identityvia OTP or a one-time email reset link and set a new password.</td></tr><tr><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">UC-05: Manage Personal Profile</td><td colspan="1" rowspan="1">Allows a logged-in Customer to view and update personal information(full name, phone number, date of birth, avatar) and change their accountpassword.</td></tr><tr><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">UC-06: Browse MoviesAndShowtimes</td><td colspan="1" rowspan="1">Allows any user to browse now-showing and upcoming movies, viewshowtimes by date with optional filters, and navigate to movie details orinitiate a booking.</td></tr><tr><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">UC-07: View Movie Details And Trailer</td><td colspan="1" rowspan="1">Allows any user to view comprehensive movie information includingmetadata, embedded trailer, customer ratings, and available showtimes,and initiate a booking directly from this page.</td></tr><tr><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">UC-08: Search And Filter Movies OrShowtimes</td><td colspan="1" rowspan="1">Allows any user to search for movies by keyword (title, director, or cast)and apply multi-criteria filters to find matching movies or showtimes.</td></tr><tr><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">UC-09: Book Tickets Online</td><td colspan="1" rowspan="1">Allows a logged-in Customer to complete an end-to-end online ticketbooking — selecting seats, optionally adding F&amp;B and discounts, andprocessing payment — resulting in a confirmed booking and QR codedelivery.</td></tr><tr><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">UC-10: Select Seats</td><td colspan="1" rowspan="1">Allows a Customer (online) or Cashier (POS) to view a real-time seat mapand select seats for a chosen showtime; selected seats are locked for ashared 10-minute session window.</td></tr><tr><td colspan="1" rowspan="1">11</td><td colspan="1" rowspan="1">UC-11: Pre-order Food &amp; Beverage</td><td colspan="1" rowspan="1">Allows a Customer to add F&amp;B items to an in-progress online bookingbefore payment, available only when the showtime starts more than 30minutes from the time of ordering.</td></tr><tr><td colspan="1" rowspan="1">12</td><td colspan="1" rowspan="1">UC-12: Apply Voucher Or PromotionCode</td><td colspan="1" rowspan="1">Allows a Customer (online) or Cashier (POS) to enter and apply a singlemanually entered voucher code as a Tier 3 discount against the ticketsubtotal of an in-progress booking.</td></tr><tr><td colspan="1" rowspan="1">13</td><td colspan="1" rowspan="1">UC-13: Process Online Payment</td><td colspan="1" rowspan="1">Processes payment for a confirmed online booking through the selectedexternal payment gateway and updates the booking status based on thegateway's callback response.</td></tr><tr><td colspan="1" rowspan="1">14</td><td colspan="1" rowspan="1">UC-14: Receive Booking ConfirmationAnd QR Code</td><td colspan="1" rowspan="1">Automatically triggered upon booking confirmation to generate a uniqueHMAC-signed QR code and deliver confirmation details to the Customervia email and SMS.</td></tr><tr><td colspan="1" rowspan="1">15</td><td colspan="1" rowspan="1">UC-15: View Booking History &amp; E-Ticket</td><td colspan="1" rowspan="1">Allows a Customer to browse their full booking history across Upcoming,Past, and Cancelled tabs, view e-ticket QR codes, and initiate cancellationfor eligible online bookings.</td></tr><tr><td colspan="1" rowspan="1">16</td><td colspan="1" rowspan="1">UC-16: Sell Tickets at Box Office</td><td colspan="1" rowspan="1">Allows a Cashier to process a walk-in ticket purchase via POS — selectinga showtime and seats, applying optional F&amp;B items and voucherdiscounts, and handing off to counter payment.</td></tr><tr><td colspan="1" rowspan="1">17</td><td colspan="1" rowspan="1">UC-17: Process Counter Payment</td><td colspan="1" rowspan="1">Allows a Cashier to collect walk-in payment via card, cash, or QR banktransfer, create the confirmed offline booking record, and trigger physicalticket printing.</td></tr><tr><td colspan="1" rowspan="1">18</td><td colspan="1" rowspan="1">UC-18: Print Physical Ticket &amp; Receipt</td><td colspan="1" rowspan="1">Prints a physical ticket for each booked seat and an itemized paymentreceipt for the walk-in customer.</td></tr><tr><td colspan="1" rowspan="1">19</td><td colspan="1" rowspan="1">UC-19: Check-in via QR Code Scan</td><td colspan="1" rowspan="1">Allows a Cashier to scan a customer's booking QR code at the cinemaentrance, validate the booking against security conditions, and mark thebooking as CHECKED_IN.</td></tr><tr><td colspan="1" rowspan="1">20</td><td colspan="1" rowspan="1">UC-20: Fulfill Food Pre-order atConcession</td><td colspan="1" rowspan="1">Allows Concession Staff to receive and fulfill F&amp;B pre-orders associatedwith a booking, triggered conditionally upon successful QR code check-inwhen an F&amp;B order exists. (Online or Offline)</td></tr><tr><td colspan="1" rowspan="1">21</td><td colspan="1" rowspan="1">UC-21: Manage F&amp;B Menu</td><td colspan="1" rowspan="1">Allows the Cinema Manager to create, update, and manage theconcession menu including item categories, descriptions, prices, andavailability status.</td></tr><tr><td colspan="1" rowspan="1">22</td><td colspan="1" rowspan="1">UC-22: Cancel Booking</td><td colspan="1" rowspan="1">Allows a Customer (online) or Cashier (at counter) to cancel an eligibleconfirmed booking and initiate the refund calculation process based onthe time-based refund policy.</td></tr><tr><td colspan="1" rowspan="1">23</td><td colspan="1" rowspan="1">UC-23: Process Refund</td><td colspan="1" rowspan="1">Allows a Cashier to process the calculated refund amount for a cancelledbooking via the appropriate method — payment gateway reversal, cash,or bank transfer.</td></tr><tr><td colspan="1" rowspan="1">24</td><td colspan="1" rowspan="1">UC-24: View Loyalty Points &amp; History</td><td colspan="1" rowspan="1">Allows a Customer to view their current loyalty points balance and fulltransaction history, including earned, redeemed, reversed, and reinstatedentries.</td></tr><tr><td colspan="1" rowspan="1">25</td><td colspan="1" rowspan="1">UC-25: Redeem Loyalty Points</td><td colspan="1" rowspan="1">Allows a Customer to apply accumulated loyalty points as a monetarydiscount against the ticket subtotal of an in-progress online booking.Points redemption is not available for walk-in purchases at the box office.</td></tr><tr><td colspan="1" rowspan="1">26</td><td colspan="1" rowspan="1">UC-26: Manage Movie Information</td><td colspan="1" rowspan="1">Allows the Cinema Manager to create, update, and manage movie recordsincluding metadata, poster, trailer URL, genre, age rating, and publicationstatus.</td></tr><tr><td colspan="1" rowspan="1">27</td><td colspan="1" rowspan="1">UC-27: Import from TMDB</td><td colspan="1" rowspan="1">Allows the Cinema Manager to search and import movie data from theTMDB external API, auto-populating movie fields to reduce manual dataentry effort.</td></tr><tr><td colspan="1" rowspan="1">28</td><td colspan="1" rowspan="1">UC-28: Manage Showtime Schedule</td><td colspan="1" rowspan="1">Allows the Cinema Manager to create, edit, publish, and manageshowtime schedules for movies across available screening rooms, subjectto showtime freeze rules.</td></tr><tr><td colspan="1" rowspan="1">29</td><td colspan="1" rowspan="1">UC-29: Manage Screening Rooms &amp;Layouts</td><td colspan="1" rowspan="1">Allows the Cinema Manager to configure screening rooms including seatlayout, room type (2D/3D/IMAX/4DX), total capacity, and maintenancestatus.</td></tr><tr><td colspan="1" rowspan="1">30</td><td colspan="1" rowspan="1">UC-30: Configure Seat Types &amp; TicketPricing</td><td colspan="1" rowspan="1">Allows the Cinema Manager to configure base ticket prices by time slot,seat-type multipliers, and fixed surcharges for premium rooms (IMAX,4DX, Dolby).</td></tr><tr><td colspan="1" rowspan="1">31</td><td colspan="1" rowspan="1">UC-31: Manage Promotions AndVoucher Campaigns</td><td colspan="1" rowspan="1">Allows the Cinema Manager to create and manage Tier 2 automaticpromotional campaigns and Tier 3 voucher codes, including discountrules, validity periods, and redemption limits.</td></tr><tr><td colspan="1" rowspan="1">32</td><td colspan="1" rowspan="1">UC-32: Submit Movie Review &amp; Rating</td><td colspan="1" rowspan="1">Allows a Customer who has attended a showtime (CHECKED_IN status) tosubmit a star rating and written review for the movie, pendingmoderation before public display.</td></tr><tr><td colspan="1" rowspan="1">33</td><td colspan="1" rowspan="1">UC-33: Moderate Movie Reviews</td><td colspan="1" rowspan="1">Allows the Cinema Manager to review, approve, or reject customer-submitted movie reviews before they are published on the public moviedetail page.</td></tr><tr><td colspan="1" rowspan="1">34</td><td colspan="1" rowspan="1">UC-34: Manage User Accounts &amp; Roles</td><td colspan="1" rowspan="1">Allows the System Admin to create, update, activate, deactivate, unlock,and manage role assignments for all staff and customer accounts in thesystem.</td></tr><tr><td colspan="1" rowspan="1">35</td><td colspan="1" rowspan="1">UC-35: Configure System Settings</td><td colspan="1" rowspan="1">Allows the System Admin to configure global system parameters includingthe public holiday calendar, service fee rates, and other operationalsettings affecting pricing and availability</td></tr><tr><td colspan="1" rowspan="1">36</td><td colspan="1" rowspan="1">UC-36: View Business Reports &amp;Dashboard</td><td colspan="1" rowspan="1">Allows the Cinema Manager and System Admin to view real-timeoperational dashboards and generate reports on revenue, bookingvolume, seat occupancy, and customer metrics.</td></tr><tr><td colspan="1" rowspan="1">37</td><td colspan="1" rowspan="1">UC-37: View Audit Log</td><td colspan="1" rowspan="1">Allows admin view audit log</td></tr><tr><td colspan="1" rowspan="1">38</td><td colspan="1" rowspan="1">UC38: Chat with AI Support</td><td colspan="1" rowspan="1">Allows a logged-in Customer to interact with an Al-powered chatbot toreceive personalized movie recommendations, showtime suggestions,and automated answers to booking-related or policy questions.</td></tr><tr><td colspan="1" rowspan="1">39</td><td colspan="1" rowspan="1">UC39:    Automated     ShowtimeReminder(System-initiated)</td><td colspan="1" rowspan="1">Automatically sends an SMS showtime reminder to Customers with aCONFIRMED booking, triggered by a scheduled system job that runsperiodically and delivers the reminder via SMS Service approximately 1hour before the showtime starts.</td></tr><tr><td colspan="1" rowspan="1">40</td><td colspan="1" rowspan="1">UC-40: Submit Identity Verification</td><td colspan="1" rowspan="1">Allows a logged-in Customer to upload images of their CCCD/CMND (frontand back) and a selfie photo for identity verification. The system forwardsthese to the external Identity Verification Service, which validates thedocuments and performs facial matching. Upon success, theCustomer's identityVerificationStatus is set to VERIFIED and verifiedDob ispopulated from the extracted data.</td></tr><tr><td colspan="1" rowspan="1">41</td><td colspan="1" rowspan="1">UC-41: Manage Seat Type Catalog</td><td colspan="1" rowspan="1">Cinema Manager can manage seat type catalog</td></tr></table>

## Permission Matrix

Permission Matrix mapping functions and user roles for Cinema Management Sy application is described as below:

“O” means that user has permission on corresponding function. For more information about what the actor can do on that function, please refer to corresponding use case.

“O\*” means that user has permission on corresponding function on the item they created. For more information about what the actor can do on that function, please refer to corresponding use case.

“X” means that user does not have permission on corresponding function.

Note: All Cinema Manager operations (UC-21, UC-26–UC-33, UC-36) are scoped to the cinema location(s) explicitly assigned to that Manager's account by System Admin (UC-34). Attempting to access or modify data belonging to an unassigned location returns HTTP 403.

<table><tr><td colspan="1" rowspan="1">Number</td><td colspan="1" rowspan="1">Function</td><td colspan="1" rowspan="1">Guest</td><td colspan="1" rowspan="1">Customer</td><td colspan="1" rowspan="1">Cashier</td><td colspan="1" rowspan="1">ConcessionStaff</td><td colspan="1" rowspan="1">CinemaManager</td><td colspan="1" rowspan="1">SystemAdmin</td></tr><tr><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">RegisterAccount</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X(ConcessionStaff accessessystem viadedicatedConcessionDisplay device(device-levelauthentication,no individuallogin required)</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">Login</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">0</td></tr><tr><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">Logout</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">0</td></tr><tr><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">ResetPassword</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">0</td></tr><tr><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">ManagePersonalProfile</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0*</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">BrowseMovies &amp;Showtimes</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">View MovieDetails &amp;Trailer</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">Search &amp;Filter</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">Book TicketsOnline</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">Select &amp; LockSeats</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">11</td><td colspan="1" rowspan="1">Pre-orderFood &amp;Beverage</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">12</td><td colspan="1" rowspan="1">ApplyVoucher /PromotionCode</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">13</td><td colspan="1" rowspan="1">ProcessOnlinePayment</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">14</td><td colspan="1" rowspan="1">ReceiveBookingConfirmationAnd QR</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">15</td><td colspan="1" rowspan="1">View BookingHistory AndE-Ticket</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0*</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">16</td><td colspan="1" rowspan="1">Sell Tickets atBox Office</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">17</td><td colspan="1" rowspan="1">ProcessCounterPayment</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">18</td><td colspan="1" rowspan="1">Print PhysicalTicket AndReceipt</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">19</td><td colspan="1" rowspan="1">Check-in viaQR Code Scan</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">20</td><td colspan="1" rowspan="1">Fulfill FoodPre-order atConcession</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">21</td><td colspan="1" rowspan="1">Manage F&amp;BMenu</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">22</td><td colspan="1" rowspan="1">CancelBooking</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0*</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">23</td><td colspan="1" rowspan="1">ProcessRefund</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">24</td><td colspan="1" rowspan="1">View LoyaltyPoints AndHistory</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0*</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">25</td><td colspan="1" rowspan="1">RedeemLoyalty Points</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0*</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">26</td><td colspan="1" rowspan="1">ManageMovieInformation</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">27</td><td colspan="1" rowspan="1">Import MovieData fromTMDB</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">28</td><td colspan="1" rowspan="1">ManageShowtimeSchedule</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">29</td><td colspan="1" rowspan="1">ManageScreeningRooms AndLayouts</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">30</td><td colspan="1" rowspan="1">ConfigureSeat TypesAnd TicketPricing</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">31</td><td colspan="1" rowspan="1">ManagePromotionsAnd Voucher</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Campaigns</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">32</td><td colspan="1" rowspan="1">Submit MovieReview AndRating</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0*</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">33</td><td colspan="1" rowspan="1">ModerateMovieReviews</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">34</td><td colspan="1" rowspan="1">Manage UserAccounts AndRoles</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td></tr><tr><td colspan="1" rowspan="1">35</td><td colspan="1" rowspan="1">ConfigureSystemSettings</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td></tr><tr><td colspan="1" rowspan="1">36</td><td colspan="1" rowspan="1">View AuditLog</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td></tr><tr><td colspan="1" rowspan="1">37</td><td colspan="1" rowspan="1">ViewBusinessReports AndDashboard</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">0</td></tr><tr><td colspan="1" rowspan="1">38</td><td colspan="1" rowspan="1">Chat with AlSupport</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">39</td><td colspan="1" rowspan="1">Manage SeatType Catalog</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td></tr><tr><td colspan="1" rowspan="1">40</td><td colspan="1" rowspan="1">SubmitIdentityVerification</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">0</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td><td colspan="1" rowspan="1">X</td></tr></table>

## Site Map

The site map describes the way for navigating through the system.

2.1.24 Zone 1: Customer Web

![](images/3e1914e440a90977eb490ec7f23119887fc58b9708703b140ca2b8ee0442cd10.jpg)

![](images/cab567a09a0e8fbc56befe1dea4490dbf0b2592a545dfd250a934fdd1a794271.jpg)

## SITE MAP· ZONE 2 ZONE 2 - POS DASHBOARD 9 màn hình ·4 nhóm chc năng · Cp nht 1/7/2026

A·POS Dashboard (Hub)

POS Home

3 nhánh chính: New Sale · Check-in · Booking Lookup

M màn hinh →

## B ▶ B · New Sale Wizard (UC-16 → UC-17 → UC-18)

## Ghi chú luồng Zone 2

## 2. Chn gh

Luồng bán vé chính (UC-16→18)

/pos/seats

1. Chn sut chiu

QR Check-in AUDIT

## C·Check-in Scanner (UC-19)

M màn hình →

M màn hình →

Chn sut → Chn gh → F&B/Voucher → Thanh toán → In vé (QR)

Quét QR · validate CBR-14 · Deny with reason (UC-39 audit)

Luồng hu vé (UC-22)

UC-16 · sort theo gi· confirm T18 · CBR-04

/pos/checkin

Lookup mã → Chn lý do → Xem % refund (CBR-05) → Xác nhn. F&B đã confirm không hoàn (BR-UC11-02).

![](images/881c5aa2f20476a8d85606851ca6edb6576945e297e0612fadd6951f517ce36d.jpg)

## 3. F&B + Voucher

/pos/fnb

Seat map · Lock 10 phút · CBR-01 M màn hình →

/pos/ticket

UC-17 · Combo · áp voucher · đồi đim

M màn hinh →

## 4. Thanh toán vAT

Edit withLovable Cash · VNPay· MoMo· VAT 5% ticket / 8% F&B / IU% service M màn hinh →

5. In vé + hoá đơn QR

M màn hinh →

UC-18·QR HMAC-signed ·A6/A7 sample

## D· Booking Lookup & Refund (UC-22)

Tra cu booking

/pos

Popup nhp mã · validate trưc khi vào flow hu M màn hình →

X Cancel ticket REFUND

/pos/cancel

Dropdown lý do (Other → free-text) · refund 70/50/30/0 · CBR-05

M màn hinh →

## Luồng check-in (UC-19)

Scan QR → Verify HMAC + trng thái + ngày → Approve / Deny (log lý do)

## VAT breakdown (BR-VAT)

Ticket 5% · F&B 8% · Service fee 10% — tách dòng trong hóa đơn

Zone 2·POS · Zone 3· Concession TV

## 2.1.26 Zone 3: Concession Display

![](images/d64331fa08905927d10dc960a209e10f9fc7389a0e91b9a01dd863ea8d4ed687.jpg)

![](images/9bb62b5fd6540a0eff7cd42ef927a5aa2519aaabb67d0b10f4b72ca7291fa5e3.jpg)

![](images/b0ea468ee7ddbc90022d81828419e2c5cd0053e2363c65a8de0d6e5e6e352cda.jpg)

![](images/5f559976a4f2e609b549db8fad857d99cb7e6b221c4b4990a8a41ec17f930125.jpg)

## 2.1.27 Zone 4: Manager Dashboard

Zone 5 →

![](images/edd1d42de83e2e4bc5222541f01e25d17e12de6077e5162609d04903ef39acc8.jpg)

SITE MAP · ZONE 4

## ZONE 4 — CINEMA MANAGER

13 màn hình · 6 nhóm chc nāng · Cp nht 1/7/2026

M app

## A·Operations Hub

SC-M01·UC-22 KPIhôm nay·doanh thu·occupancy·alerts

SC-M06 - UC-36 Weekly KPI · split doanh thu · share vi Admin

![](images/3435175afd1fbe8c8591181976be2384b1ced20b496fa6eda343318947fbd0fc.jpg)

## BB· Movie Management (UC-26·UC-27)

SC-M02· UC-23 Now showing / Coming soon · card grid + poster

## Add movie NEW

UC-26Poster upload·metadata·draft→ published

UC-26 Pre-fll form·delete·save changes (demo #6)

## Import from TMDB NEW

UC-27 Search TMDB·preview poster- 1-click import

![](images/546f44da26544b13b0948527b648fac18c0762ea4864cfbb22a7d34847625a2b.jpg)

## C· Showtime Schedule (UC-28)

SC-M03-·UC-24 Grid theo phòng × già · conflict detection

UC-28 Auto end-time ·price preview·CBR guard

## Calendar & Holidays NEW

UC-35 Public/Specialevent/Maintenance·recurring

## Manage room (seat grid) NEW

## D 血D· Screening Rooms & Layouts (UC-29)

## Seat Type Catalog NEW

uC-29 4-way scree·drag-paint·sweet lane·tech lane

UC-NEW Standard·VIP·Sweetbox·Accessible·multiplier

M màn hình →

M màn hinh →

M màn hinh →

M màn hình →

M màn hinh →

M màn hình →

M màn hinh →

M màn hình →

M màn hình →

## E· Pricing & Promotions (UC-25 · UC-31)

M màn hinh →

sC-M04-UC-25 Tier × ngày× giò·multiplier-surcharge

Mò màn hinh →

M màn hình →

SC-M05·UC-26 Danh sách campaign · trang thái·usage

M màn hinh →

UC-31 Tier 2/3·batch codes·35% discount cap

![](images/a4d9363148304b778cb1f86a71df3d7eac8dc85209d3c47541161635fda7563b.jpg)

## F· F&B Menu Management (UC-30)

F&B Menu NEW

M màn hinh →

UC-21·UC-30 Category filter·combo·availability·add item modal

## Ghi chú luöng Zone 4

Luồng to phim (UC-26 → UC-27) Movies catalog → Add movie (poster + metadata) hoc Import TMDB → Draft → Publish

Luồng cu hinh phòng (UC-29 + UC-NEW) Seat Type Catalog đinh nghia tier → Manage Room dùng lai tier (drag-to-paint - sweet lane ·tech lane đoi diên màn hinh)

Luồng xp sut chiu (UC-28) Chon phim → chon phòng → Add showtime (auto end-time + price preview) → check conflict vái Calendar.

Luồng giá + voucher (UC-25 · UC-31) Pricing matrix set base × multiplier → New campaign apply discount, cap 35% theo policy

Zone 4· Cinema Manager·Zone 5· Admin Panel →

2.1.28 Zone 5: Admin Panel

![](images/85ec1dd4f20b78b846d878745bb112beca09dd48ad380be1be730db80c00778f.jpg)

## BB·System Configuration (UC-35)

System settings

/admin/settings

SC-A03·UC-35 Tên chuôi rap·logo·currency·timezone ·locale

## Tax & finance rules

/admin/settings/tax

UC-35 VAT ticket 5% · VAT F&B 8% · service fee 10% · rounding

## C · Dashboard & Reports (UC-36) — shared vi Manager

品Ops dashboard sHARED

/dashboard

SC-A0x·UC-36 Shared vi Manager ·Admin xem toàn h thőng, Manager xem chi nhánh · KPI realtime

## Cross-cinema reports

/admin/reports

SC-A0x · UC-36 Tng hp doanh thu toàn h thng · so sánh chi nhánh ·export CSV/PDF

## DD· Audit Log (UC-37)

Audit trail AUDIT

/admin/audit

SC-A04·UC-37 Ai·làm gi ·lúc nào·IP·trưc / sau · filter theo entity

## Ghi chú luồng Zone 5

## Luồng to tài khon (UC-34)

Accounts → Create → chon role + cinema → gi email invite → user set password (theo policy).

## Dashboard & Reports shared (UC-36)

Dashboard + Reports dùng chung cho Admin & Manager ·Admin scope toàn h thng, Manager scope chi nhánh.

## Luồng cu hình h thng (UC-35)

System settings → Tax & finance (VAT 5% / 8%, service fee 10%) → apply toàn h thng.

## Luồng audit (UC-37)

Moi hành đng ghi log · filter theo entity/user/time · diff trưc-sau · export cho co

## 3. Use Case Specifications

This section covers the system’s functional requirements which details what the system must do in terms of input, behavior and the expected output. It elicits the interaction between the actor(s) and the system, the system’s behavior and the results of their interactions.

## Authentication & Account

3.1.1 UC-01: Register Account
<table><tr><td>Objective:</td><td>This use case allows a Guest (unauthenticated user) to create a new Customer account by providing personal information and verifying their identity via a 6-digit OTP sent to their</td></tr><tr><td></td><td>registered email.</td></tr><tr><td>Primary Actor: Seondary Actor:</td><td>Guest (unauthenticated user)</td></tr><tr><td>Trigger:</td><td>Email Service Guest navigates to the Sign Up / Registration page and decides to create a new</td></tr><tr><td rowspan="2">Pre-condition:</td><td>account.</td></tr><tr><td>- Guest does not have an existing account in the system. - Guest has access to the registration page.</td></tr><tr><td rowspan="3">Post-condition:</td><td>- Guest has a valid email address and phone number.</td></tr><tr><td>- A new Customer account is created with status = ACTIVE and role = CUSTOMER.</td></tr><tr><td>- The Guest is automatically logged in (JWT token / session created).</td></tr><tr><td rowspan="5">Main Flow:</td><td>- The Guest is redirected to the Homepage.</td></tr><tr><td>- A welcome email is sent to the registered email address (optional, recommended).</td></tr><tr><td>1. Guest navigates to the Registration page.</td></tr><tr><td>2. System displays Step 1: Information form with fields: Display Name, Email, Phone Number, Password, Confirm Password.</td></tr><tr><td>3. Guest fills in all required information.</td></tr><tr><td rowspan="14">Alternative Flow:</td><td></td></tr><tr><td></td></tr><tr><td>4. Guest clicks "Gi mã OTP" button.</td></tr><tr><td>5. System validates all inputs (email uniqueness, password policy, phone format, etc.)</td></tr><tr><td>6. System generates a 6-digit OTP and sends it to the Guest's email.</td></tr><tr><td>7. System switches to Step 2: OTP Verification screen.</td></tr><tr><td>8. Guest enters the 6-digit OTP.</td></tr><tr><td>9. System verifies the OTP (CBR-15).</td></tr><tr><td>10. System creates the new Customer account (status = ACTIVE).</td></tr><tr><td>11. System automatically logs in the Guest and creates JWT token. 12. System sends Welcome Email (ET-01).</td></tr><tr><td>14. Use case ends successfully.</td></tr><tr><td>13. System redirects the Guest to the Homepage.</td></tr><tr><td></td></tr><tr><td></td></tr><tr><td></td></tr><tr><td rowspan="14"></td><td>AF1: Resend OTP: At the OTP input screen (after Main Flow step 8):</td></tr><tr><td></td></tr><tr><td>1. Guest realizes the OTP has not arrived or has expired</td></tr><tr><td>2. Guest clicks “Gi li mã” button 3. System checks the time since the last OTP sent:</td></tr><tr><td>+ If less than 60 seconds have passed =&gt; display “Vui lòng ch ít nht 60s trưc khi</td></tr><tr><td>yêu cu mã mi” =&gt; return to OTP input screen</td></tr><tr><td>+ If 60 seconds or more have passed =&gt; continue</td></tr><tr><td>4. System generates a new 6-digit OTP (valid for 5 minutes) and overwrites the old OTP in cache</td></tr><tr><td>5. System sends the new OTP via email (Secondary Actor: Email Service) 6. System displays a message: “Mã OTP mi đã đưc gi qua email ca bn”</td></tr><tr><td>7. System resets the incorrect attempt counter to 0 8. Guest enters the new OTP</td></tr><tr><td>9. Flow continues at Main Flow step 10 (OTP verification)</td></tr><tr><td>AF2: Edit info before verification: At the OTP input screen (after Main Flow step 8).</td></tr><tr><td></td></tr><tr><td>1. Guest realizes that the previously entered information (name, email, ect,) is incorrect and need to change.</td></tr><tr><td>2. Guest clicks the “Edit information" button 3. System redisplays the registration form, pre-flling all previously entered data (except old OTP) from temporary storage.</td></tr><tr><td rowspan="14"></td><td>4. Guest corrects the information 5. Guest clicks the “Send OTP buttion"</td></tr><tr><td>6. System re-validates all input data (Same as Main Flow step 5)</td></tr><tr><td></td></tr><tr><td>7. System generates a new 6-digit OTP, invalidating the old one</td></tr><tr><td>8. System sends the new OTP via email</td></tr><tr><td>9. System displays the OTP input screen again</td></tr><tr><td>10. Flow continues at Main Flow step 10 (OTP verification)</td></tr><tr><td>AF3: Auto-fill OTP: After OTP is sent, OTP input screen is displayed (after Main Flow step 8).</td></tr><tr><td>1. System (browser) requests permission to access the user's email inbox (if not already</td></tr><tr><td>grandted)</td></tr><tr><td>2. Guest grants permission</td></tr><tr><td>3. System calls the email APl to read the most recent email from the inbox 4. System extracts a 6-digit OTP from the email body (using regext pattern matching)</td></tr><tr><td>5. System automatically fills the extracted OTP into the input field</td></tr><tr><td>6. System automatically clicks “Verify" button (or prompts Guest to click that button) 7. Flow continues at Main Flow step 10 (OTP verification)</td></tr><tr><td>Exception Flow: EF1: Email already exists: Stop at step 5. Show error message.</td></tr><tr><td>EF2: Invalid Information Input: Stop at step 5. Show format example.</td></tr><tr><td></td></tr><tr><td>EF3: Password confirmation mismatch: Stop at step 5. Show mismatch error.</td></tr><tr><td>EF4: Incorrect OTP: Stop at step 10. Show attempts left. Lock after 3 failures.</td></tr><tr><td>EF5: OTP expired: Stop at step 10. Show expired message + resend button.</td></tr><tr><td>EF6: Email sending fails: Stop at step 7. Show error. Do not save data.</td></tr><tr><td>Business Rules: CBR-15: OTP Validation</td></tr><tr><td>BR-UC01-01: Unique Email Constraint: Email address must be globally unique across the</td></tr><tr><td>system. Attempting to register with an already-registered email is rejected immediately.</td></tr><tr><td>BR-UC01-02: Password Policy: Password must be minimum 8 characters, contain at least one</td></tr><tr><td>letter (a-z, A-Z) and at least one digit (0–9). Special characters are optional but allowed.</td></tr><tr><td>BR-UC01-03: Phone Number Format: Phone number must be a valid Vietnamese mobile or</td></tr><tr><td>landline format (10–11 digits starting with 0, or international format +84). Format validation</td></tr><tr><td>occurs in real-time.</td></tr><tr><td>BR-UC01-04: Account Auto-Activation: Upon successful OTP verification, the account is</td></tr><tr><td>immediately activated (status = ACTIVE) without requiring additional email confirmation.</td></tr><tr><td>BR-UC01-05: Auto-Login After Registration: Immediately after account creation, the system</td></tr><tr><td>automatically logs in the new Customer using the credentials provided during registration. No</td></tr><tr><td>manual login is required.</td></tr><tr><td>BR-UC01-06: Full Name Validation: Full Name must be between 2 and 100 characters. Empty</td></tr><tr><td>or whitespace-only names are rejected.</td></tr></table>

3.1.2 UC-02: Login
<table><tr><td rowspan="2">Objective:</td><td>Allows an authenticated Actor to access the system using registered credentials or Google</td></tr><tr><td rowspan="2">account, and be redirected to their role-appropriate interface.</td></tr><tr><td rowspan="2">Primary Actor:</td></tr><tr><td>All Actors (Customer, Cashier, Concession Staff, Cinema Manager, System Admin)</td></tr><tr><td>Secondary Actor</td><td>Google OAuth Service</td></tr><tr><td rowspan="2">Trigger:</td><td>Actor navigates to the Login page and submits credentials or selects GoogleSign-In.</td></tr><tr><td>- Actor is not currently logged in.</td></tr><tr><td rowspan="2">Pre-condition: Post-condition:</td><td>- Actor has an existing account in the system.</td></tr><tr><td>- A JWT token/session is created for the Actor.</td></tr><tr><td rowspan="2">Main Flow</td><td>- Actor is redirected to the role-appropriate page.</td></tr><tr><td>1. Actor navigates to the Login page. 2. System displays login form with Email, Password, &quot;Đăng nhp&quot; button, &quot;Đăng</td></tr><tr><td></td><td>nhp vi Google&quot; button, and &quot;Quên mt khu?&quot; link.</td></tr><tr><td rowspan="8"></td><td>3. Actor enters Email and Password.</td></tr><tr><td>4. Actor clicks &quot;Đăng nhp&quot;.</td></tr><tr><td>5. System validates credentials and account status.</td></tr><tr><td>6. System creates JWT token.</td></tr><tr><td>7. System redirects Actor based on role (Customer → Homepage).</td></tr><tr><td>8. Use case ends successfully.</td></tr><tr><td>AF1: Forgot Password — At step 3, Actor clicks &quot;Quên mt khu?&quot;</td></tr><tr><td>1. System redirects Actor to the Reset Password page.</td></tr><tr><td rowspan="8"></td><td></td></tr><tr><td>2. Flow continues at UC04.</td></tr><tr><td>AF2: Login with Google:</td></tr><tr><td>1. Actor clicks &quot;Đăng nhp vi Google&quot; on the Login page. 2. System redirects Actor to the Google OAuth consent screen (via Google OAuth</td></tr><tr><td>Service). 3. Actor selects or confirms their Google account. 4. Google OAuth Service authenticates and returns Actor&#x27;s verified email and profile to</td></tr><tr><td>the system. 5. System checks whether an account with the returned email exists in the system.</td></tr><tr><td>6. If account found and status = ACTIVE: System creates a JWT token / session and links the Google credential to the account (first-time only).</td></tr><tr><td>7. System redirects Actor based on role (same as Main Flow step 10). 8. Flow ends successfully. EF1: Email not found or password incorrect. Stop at step 5 or 6. Show: &quot;Email or password is</td></tr><tr><td rowspan="10">Exception Flow</td><td></td></tr><tr><td>incorrect.&quot;</td></tr><tr><td></td></tr><tr><td>EF2: Failed login count reaches 5. Stop at step 8. Lock account for 15 minutes. Show: &quot;Quá</td></tr><tr><td>nhiu ln nhp sai. Tài khon ca bn b tm khóa, ch 15 phút đ th li&quot; (BR-UC02-01)</td></tr><tr><td>EF3: Account within lockout period. Stop at step 8. Show: &quot;Your account is temporarily locked. Please try again later or contact support.&quot;</td></tr><tr><td>EF4: Account status = INACTIVE. Stop at step 7. Show: &quot;Tài khon này tm thi không hot</td></tr><tr><td>đng, Vui lòng liên h dch v h tr.&quot;</td></tr><tr><td>EF5: Google email not registered in system (AF2). Stop at AF2 step 5. Show: &quot;Không tìm thãy tài</td></tr><tr><td>khon nào cho tài khon Google này. Vui lòng đăng ký bng email trưc.&quot;</td></tr><tr><td rowspan="4">Provide link to Registration page.</td><td></td></tr><tr><td>EF6: Google OAuth Service unavailable or Actor denies permission (AF2). Stop at AF2 step 3.</td></tr><tr><td>Show: &quot;Hin không th đăng nhp bng Google. Vui lòng s dng email và mt khu thay th.&quot;</td></tr><tr><td>Return to Login page.</td></tr><tr><td rowspan="8">Business</td><td></td></tr><tr><td>CBR-17</td></tr><tr><td></td></tr><tr><td>BR-UC02-01: Account Lockout — After 5 consecutive failed login attempts via email/password,</td></tr><tr><td>the account is locked for 15 minutes automatically. The counter resets to 0 after a successful</td></tr><tr><td></td></tr><tr><td>login or after the lockout period expires. System Admin can manually unlock the account via</td></tr><tr><td>UC34. Google OAuth login failures do not increment this counter.</td></tr></table>

## 3.1.3 UC-03: Logout

<table><tr><td></td><td>Login page.</td></tr><tr><td>Primary Actor:</td><td>All authenticated Actors</td></tr><tr><td>Secondary Actor:</td><td>None</td></tr><tr><td>Trigger:</td><td>Actor clicks the &quot;Logout&quot; button from any page.</td></tr><tr><td>Pre-condition:</td><td>- Actor is currently logged in with an active session.</td></tr><tr><td>Post-condition:</td><td>- Actor&#x27;s JWT token / session is invalidated server-side.</td></tr><tr><td></td><td>- All authentication cookies are cleared from the browser.</td></tr><tr><td>Main Flow:</td><td>- Actor is redirected to the Login page.</td></tr><tr><td></td><td>1. Actor clicks the &quot;Logout&quot; button from the navigation menu.</td></tr><tr><td></td><td>2. System invalidates the Actor&#x27;s JWT token / session server-side.</td></tr><tr><td></td><td>3. System clears all authentication cookies from the browser.</td></tr><tr><td></td><td>4. System redirects Actor to the Login page.</td></tr><tr><td></td><td>5. System displays confirmation: &quot;You have been logged out successfully.&quot;</td></tr><tr><td></td><td>6. Use case ends successfully.</td></tr><tr><td>Alternative Flow:</td><td>None</td></tr><tr><td>Exception Flow:</td><td>EF1: Session already expired before logout action. Stop at step 2. System detects no active session — redirect to Login page silently without error.</td></tr><tr><td>Business Rules:</td><td>None</td></tr></table>

3.1.4 UC-04: Reset Password
<table><tr><td>Objective:</td><td>Allows an Actor who has forgotten their password to verify their identity via a 6-digit OTP sent</td></tr><tr><td></td><td>to their registered email and set a new password. A reset-link method is also supported as an alternative.</td></tr><tr><td>Primary Actor:</td><td>Customer, Cashier, Cinema Manager, System Admin</td></tr><tr><td>Secondary Actor:</td><td>Email Service</td></tr><tr><td>Trigger:</td><td>Actor clicks "Quên mt khâu?" on the Login page.</td></tr><tr><td>Pre-condition:</td><td>- Actor is not currently logged in.</td></tr><tr><td></td><td>- Actor has an existing ACTIVE account in the system.</td></tr><tr><td></td><td>- Actor has access to their registered email address.</td></tr><tr><td>Post-condition:</td><td>- Actor's password is updated with the new password.</td></tr><tr><td></td><td>- All existing active sessions for the account are invalidated.</td></tr><tr><td></td><td>- A confirmation email is sent to the registered email address.</td></tr><tr><td>Main Flow (OTP</td><td>1. Actor clicks "Quên mt khu?" on Login page.</td></tr><tr><td>Method):</td><td>2. System displays Step 1: Enter Email and select verification method (default: Send OTP).</td></tr><tr><td></td><td></td></tr><tr><td></td><td>3. Actor enters Email and clicks "Tip tc".</td></tr><tr><td></td><td>4. System sends 6-digit OTP to the registered email.</td></tr><tr><td></td><td>5. System switches to Step 2: OTP Verification.</td></tr><tr><td></td><td>6. Actor enters OTP and confirms.</td></tr><tr><td></td><td>7. System switches to Step 3: Set New Password.</td></tr><tr><td></td><td>8. Actor enters New Password and Confirm Password.</td></tr><tr><td></td><td>9. Actor clicks "Đt li mt khu".</td></tr><tr><td></td><td>10. System updates the password and invalidates all existing sessions.</td></tr><tr><td></td><td>11. System sends password reset confirmation email.</td></tr><tr><td></td><td>12. System redirects Actor to Login page with success message.</td></tr><tr><td></td><td>13. Use case ends successfully.</td></tr><tr><td>Alternative Flow:</td><td>AF1: Reset via Email Link (at step 3, Actor selects “Gi li link reset" instead):</td></tr><tr><td rowspan="5">AF2: Resend OTP (at OTP verification screen — after Main Flow step 8):</td><td>reset link via Email Service. 2. Actor receives the email and clicks the reset link.</td></tr><tr><td></td></tr><tr><td>3. System validates token: exists, not expired, not previously used.</td></tr><tr><td>4. If valid: System displays the Set New Password form.</td></tr><tr><td>5. Flow continues at Main Flow step 12.</td></tr><tr><td>Exception Flow:</td><td>0 If &lt; 60 seconds: Show "Vui lòng đi ít nht 60s trưc khi yêu cu mã mi" Return to OTP screen. If ≥ 60 seconds: Continue. 3. System generates a new OTP, immediately invalidates the old one. 4. System sends new OTP via Email Service. 5. System resets incorrect attempt counter to 0. 6. System displays: "Mã OTP mi đã đưc gi qua email ca bn." 7. Flow continues at Main Flow step 9. Dưi đây là ni dung đã đưc dch các thông báo sang ting Vit và gi nguyên toàn b cu</td></tr><tr><td></td><td>trúc, mã li cũng như các bưc k thut cho bn: EF1: Email not found. Stop at step 5. Show generic message: "Nu email này đã đưc đăng ký, bn s nhn đưc mã OTP khôi phc trong chc lát." (Do not confirm or deny existence.) EF2: Incorrect OTP. Stop at step 10. Show: "Mã OTP không chính xác. Còn li X lân th." Lock OTP after 3 failures. EF3: OTP expired. Stop at step 10. Show: "Mã OTP này đã ht hn." Display "Gi Ii mã OTP" button. EF4: Reset link expired (AF1 only). Stop at AF1 step 3. Show: "Đưng dn này đã ht hn. Vui lòng yêu cu mt đưng dn mi." EF5: Reset link already used (AF1 only). Stop at AF1 step 3. Show: "Đưng dn này đã đưc s dung." EF6: New password same as current password. Stop at step 14. Show: "Mt khu mi phi khác</td></tr><tr><td>Business Rules:</td><td>vi mt khu hin ti ca bn." (BR-UC04-02) EF7: Email sending fails. Stop at step 7. Show error. Do not save any data. CBR-17 CBR-15: OTP Validation — 6-digit OTP, 5-minute expiry, max 3 incorrect attempts, max 3 resends per 15-minute window. BR-UC04-01: Password Policy — New password must be minimum 8 characters, contain at least one letter (a-z or A-Z) and at least one digit (0–9). Optional Characters are optional but allowed BR-UC04-02: Password Reuse Restriction — New password must differ from the currently stored password.</td></tr></table>

3.1.5 UC-05: Manage Personal Profile
<table><tr><td>Objective:</td><td>Allows a logged-in Customer to view and update their personal information, and to change their</td></tr><tr><td></td><td>account password when they know their current password.</td></tr><tr><td>Primary Actor:</td><td>Customer</td></tr><tr><td>Secondary Actor:</td><td>None</td></tr><tr><td>Trigger:</td><td>Customer navigates to My Account -&gt; Profile.</td></tr><tr><td>Pre-condition:</td><td>Customer is logged in.</td></tr><tr><td>Post-condition:</td><td>- Updated profile information is saved to the system.</td></tr><tr><td></td><td>- If password was changed: all sessions on other devices are invalidated; current session remains active.</td></tr><tr><td>Main Flow:</td><td></td></tr><tr><td></td><td>1. Customer navigates to My Account → Profile.</td></tr><tr><td></td><td>2. System displays current profile: Full Name, Phone Number, Date of Birth, Avatar. Email field is</td></tr><tr><td></td><td>displayed as read-only (BR-UC05-03).</td></tr><tr><td></td><td>3. Customer clicks "Edit Profile".</td></tr><tr><td></td><td>4. System enables editable fields: Full Name, Phone Number, Date of Birth, Avatar</td></tr><tr><td></td><td>5. Customer updates desired fields.</td></tr><tr><td></td><td>6. Customer clicks "Save Changes".</td></tr><tr><td></td><td>7. System validates all inputs (BR-UC05-01, BR-UC05-02).</td></tr><tr><td></td><td>8. System saves updated information.</td></tr><tr><td></td><td>9. System displays: "Your profile has been updated successfully."</td></tr><tr><td>Alternative Flow:</td><td>10. Use case ends successfully.</td></tr><tr><td></td><td>AF1: Change Password (Customer knows current password — accessible via My Account →</td></tr><tr><td></td><td>Security):</td></tr><tr><td></td><td>1. Customer navigates to My Account → Security → Change Password. 2. System displays the Change Password form: Current Password, New Password, Confirm</td></tr><tr><td></td><td>New Password.</td></tr><tr><td></td><td>3. Customer fills in al fields and clicks "Update Password".</td></tr><tr><td></td><td>4. System verifies Current Password matches the stored hash (BR-UC05-04).</td></tr><tr><td></td><td>5. System validates New Password (BR-UC04-01) and confirms it differs from current password (BR-UC04-02).</td></tr><tr><td></td><td>6. System updates the password hash.</td></tr><tr><td></td><td>7. System invalidates all active sessions on other devices. Current session remains active.</td></tr><tr><td></td><td>8. System displays: "Password updated. Other active sessions have been signed out."</td></tr><tr><td></td><td>9. Flow ends.</td></tr><tr><td></td><td>AF2: Update Avatar (during edit mode — after Main Flow step 4):</td></tr><tr><td></td><td>1. Customer clicks "Upload Avatar".</td></tr><tr><td></td><td>2. System opens file picker. Accepted: JPG, PNG, WEBP. Max size: 2 MB.</td></tr><tr><td></td><td>3. Customer selects image → System shows a square crop preview.</td></tr><tr><td></td><td>4. Customer confirms → Avatar is saved upon "Save Changes" (Main Flow step 6).</td></tr><tr><td>Exception Flow:</td><td></td></tr><tr><td></td><td>EF1: Phone number already registered to another account. Stop at step 7. Show: "This phone number is already linked to another account."</td></tr><tr><td></td><td></td></tr><tr><td></td><td>EF2: Invalid phone number format. Stop at step 7. Show format example.</td></tr><tr><td></td><td>EF3: Invalid Full Name (empty or exceeds 100 characters). Stop at step 7. Show: "Full Name must be between 2 and 100 characters."</td></tr><tr><td></td><td>EF4: Current password incorrect (AF1). Stop at AF1 step 4. Show: "Current password is</td></tr><tr><td></td><td>incorrect."</td></tr><tr><td></td><td>must be different from your current password." EF6: Avatar file exceeds 2 MB or unsupported format (AF2). Stop at AF2 step 2. Show: "File must be JPG, PNG, or WEBP and under 2 MB."</td></tr><tr><td>Business Rules:</td><td>CBR17 BR-UC05-01: Phone Format — Must follow valid Vietnamese format (10–11 digits starting with</td></tr><tr><td></td><td>0, or +84 international format). BR-UC05-02: Full Name Validation — 2–100 characters; empty or whitespace-only values are rejected.</td></tr><tr><td></td><td>BR-UC05-03: Email Non-Editable — Email address cannot be modified after account creation as</td></tr><tr><td></td><td>it is the primary account identifier.</td></tr><tr><td></td><td>BR-UC05-04: Current Password Verification — A password change via this UC requires the Actor</td></tr><tr><td></td><td>to provide their current password first. This distinguishes it from UC04 (Reset Password), which</td></tr><tr><td></td><td></td></tr><tr><td></td><td>is used when the password is forgotten.</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr></table>

## Movie & Showtime Discovery

3.2.1 UC-06: Browse Movies And Showtimes
<table><tr><td>Objective:</td><td>Allows any user to browse now-showing and upcoming movies, view showtimes by date with optional filters, and navigate to movie details or initiate booking.</td></tr><tr><td>Primary Actor:</td><td>Guest, Customer</td></tr><tr><td>Secondary Actor:</td><td>None</td></tr><tr><td>Trigger:</td><td>Actor visits the Homepage or navigates to the Movies section.</td></tr><tr><td>Pre-condition:</td><td>- At least one movie with status = NOW_SHOWING or COMING_SOON exists in the system.</td></tr><tr><td>Post-condition:</td><td>- Actor has browsed the movie listing and/or showtimes.</td></tr><tr><td>Main Flow:</td><td>1. Actor navigates to the Homepage. 2. System displays Hero Banner carousel, Now Showing / Coming Soon tabs, and Quick</td></tr><tr><td></td><td>Booking widget. 3. Actor selects a date from the date picker (defaults to today).</td></tr><tr><td></td><td></td></tr><tr><td></td><td>4. System displays movie grid with posters, titles, ratings, and basic showtime info.</td></tr><tr><td></td><td>5. Actor optionally applies filters (Genre, Language, Room Type, etc.).</td></tr><tr><td></td><td>6. System updates results in real-time.</td></tr><tr><td></td><td>7. Actor clicks a movie poster or title → navigates to UC-07 (Movie Detail).</td></tr><tr><td></td><td>8. Actor clicks a specific showtime directly:</td></tr><tr><td></td><td> If logged in as Customer → proceeds to UC-09 (Booking) with showtime pre-</td></tr><tr><td></td><td>filled.</td></tr><tr><td></td><td>If Guest → prompts to log in. 9. Use case ends successfully.</td></tr><tr><td>Alternative Flow:</td><td></td></tr><tr><td></td><td>AF1: No showtimes available on selected date:</td></tr><tr><td></td><td>1. At step 4, no showtimes exist for the selected date.</td></tr><tr><td></td><td>2. System displays: "No showtimes available for this date. Please try another date."</td></tr><tr><td></td><td>3. System highlights the nearest date with available showtimes on the date picker.</td></tr><tr><td></td><td>4. Actor selects a new date. Flow returns to step 4.</td></tr><tr><td></td><td>AF2: Quick Booking – Actor uses the quick booking widget on homepage to select Movie → Date → Showtime directly. (for Customer only)</td></tr><tr><td></td><td></td></tr><tr><td>Exception Flow:</td><td>EF1: No movies in system (no NOW_SHOWING or COMING_SOON titles exist). Show empty</td></tr><tr><td></td><td>state: "No movies currently available. Please check back soon."</td></tr><tr><td>Business Rules:</td><td>None</td></tr></table>

## 3.2.2 UC-07: View Movie Details And Trailer

<table><tr><td>Objective:</td><td>Allows any user to view comprehensive information about a specific movie — including metadata, trailer, customer ratings, and available showtimes — and to initiate a booking from</td></tr><tr><td></td><td>the movie detail page.</td></tr><tr><td>Primary Actor:</td><td>Guest, Customer</td></tr><tr><td>Secondary Actor:</td><td>Movie Content Provider (TMDB API)</td></tr><tr><td>Trigger:</td><td>Actor clicks on a movie title or poster from any listing page.</td></tr><tr><td>Pre-condition:</td><td>- Movie record with matching ID exists in system with status ≠ HIDDEN</td></tr><tr><td>Post-condition:</td><td>- Actor has viewed the movie&#x27;s full details and available showtimes.</td></tr><tr><td>Main Flow:</td><td>- If Actor clicks &quot;Book Now&quot;: UC09 is initiated (login required for Guest).</td></tr><tr><td></td><td>Main Flow:</td></tr><tr><td></td><td>1. Actor clicks a movie card from Homepage or listing.</td></tr><tr><td></td><td>2. System displays Movie Detail page with:</td></tr><tr><td></td><td>0Large poster, title, genre tags, duration, age rating badge, release date.</td></tr><tr><td></td><td> Embedded trailer player.</td></tr><tr><td></td><td> Synopsis, director, cast.</td></tr><tr><td></td><td> Average rating and review count.</td></tr><tr><td></td><td>3. If the movie has age restriction (T16/T18/K), system displays appropriate warning banner (CBR-04).</td></tr><tr><td></td><td>4. System displays Showtimes section on the right with date picker and available</td></tr><tr><td></td><td>showtimes grouped by time/room.</td></tr><tr><td></td><td>5. Actor selects a different date → showtimes update accordingly.</td></tr><tr><td></td><td>6. Actor clicks &quot;Đt vé ngay&quot; on a showtime:</td></tr><tr><td></td><td> If Customer (logged in) → go to UC-09 (Seat Selection) with showtime pre-</td></tr><tr><td></td><td>selected.</td></tr><tr><td></td><td>If Guest → show login prompt: &quot;Vui lòng đăng nhp đ đt vé” 7. Actor can scroll down to view approved customer reviews.</td></tr><tr><td></td><td>8. Use case ends.</td></tr><tr><td></td><td></td></tr><tr><td>Alternative Flow:</td><td>AF1: No showtimes available for selected date:</td></tr><tr><td></td><td>1. At step 5, no showtimes exist for that date.</td></tr><tr><td></td><td>2. System displays: &quot;Không có sut chiu trong ngày này&quot;</td></tr><tr><td></td><td>3. System highlights nearest available date on the picker.</td></tr><tr><td></td><td>4. Actor selects a different date or returns to browsing.</td></tr><tr><td>Exception Flow:</td><td>EF1: Movie not found or HIDDEN. Show: &quot;Movie not found or no longer available.&quot; Redirect to</td></tr><tr><td></td><td>Homepage. EF2: Trailer URL unavailable or broken. Hide trailer section silently. Display poster image in its</td></tr><tr><td></td><td>place. EF3: Movie Content Provider (TMDB) unavailable. Display locally stored metadata only. No</td></tr><tr><td>Business Rules:</td><td>disruption to the page. CBR-04: Age Restriction (T16 and T18 films display an age-restriction banner on this page. T18</td></tr></table>

## Online Ticket Booking

## 3.2.3 UC-08: Search And Filter Movies Or Showtimes

<table><tr><td colspan="1" rowspan="1">Objective:</td><td colspan="2" rowspan="1">Allows any user to search for movies by keyword and can apply filters to find matching moviesor showtimes.</td></tr><tr><td colspan="1" rowspan="1">Primary Actor:</td><td colspan="2" rowspan="1">Guest, Customer</td></tr><tr><td colspan="1" rowspan="1">Secondary Actor:</td><td colspan="2" rowspan="1">None</td></tr><tr><td colspan="1" rowspan="1">Trigger:</td><td colspan="2" rowspan="1">Actor visits the Homepage or navigates to the Movies section.</td></tr><tr><td colspan="1" rowspan="1">Pre-condition:</td><td colspan="2" rowspan="1">None</td></tr><tr><td colspan="1" rowspan="1">Post-condition:</td><td colspan="2" rowspan="1">- Actor views a filtered list of movies and/or showtimes matching the search criteria. - - Actor</td></tr><tr><td></td><td colspan="2">can navigate to UC07 or UC09 from any result</td></tr><tr><td>Main Flow:</td><td></td><td>1. Actor clicks the global search bar in the navigation header.</td></tr><tr><td></td><td></td><td>2. Actor begins typing a keyword (movie title, director name, or cast member name).</td></tr><tr><td></td><td></td><td>3. System displays real-time autocomplete suggestions (debounced at 300 ms):</td></tr><tr><td></td><td></td><td> Matching movie titles.</td></tr><tr><td></td><td></td><td>oMatching director or actor names.</td></tr><tr><td></td><td>4. Actor either:</td><td></td></tr><tr><td></td><td>0</td><td>Clicks an autocomplete suggestion → System navigates directly to UC07 for that</td></tr><tr><td></td><td>movie.</td><td></td></tr><tr><td></td><td></td><td>Presses Enter  System navigates to the full Search Results page.</td></tr><tr><td></td><td></td><td>5. System displays Search Results grouped by relevance, showing matching movie cards.</td></tr><tr><td></td><td></td><td>6. Actor applies filters from the Filter panel:</td></tr><tr><td></td><td></td><td>Genre (multi-select), Age Rating, Date, Time Slot (Morning / Afternoon /</td></tr><tr><td></td><td></td><td>Evening), Language, Room Type (2D / 3D / IMAX / 4DX).</td></tr><tr><td></td><td></td><td>7. System updates results in real-time as each filter is applied or removed.</td></tr><tr><td></td><td></td><td>8. Actor clicks a movie card → UC07. Actor clicks a showtime → UC09 (login required if</td></tr><tr><td></td><td>Guest).</td><td></td></tr><tr><td></td><td>9. Use case ends.</td><td></td></tr><tr><td>Alternative Flow:</td><td></td><td>AF1: Actor uses Filter panel without entering a keyword:</td></tr><tr><td></td><td></td><td>1. Actor opens the Filter panel directly from the Movies page without typing a</td></tr><tr><td></td><td>keyword.</td><td>2. Actor applies one or more filters.</td></tr><tr><td></td><td></td><td>3. System returns all movies matching the selected filters.</td></tr><tr><td></td><td></td><td>4. Flow continues from step 7.</td></tr><tr><td>Exception Flow:</td><td></td><td></td></tr><tr><td></td><td></td><td>EF1: No results match keyword and filters. Show: "No results found for '[keyword]'. Try different</td></tr><tr><td></td><td></td><td>keywords or clear some filters." Provide "Clear all filters" button.</td></tr><tr><td></td><td></td><td>EF2: Keyword fewer than 2 characters entered. System does not trigger search or show</td></tr><tr><td></td><td>autocomplete. No error displayed.</td><td></td></tr></table>

3.1.6 UC-09: Book Tickets Online

<table><tr><td rowspan=1 colspan=1>Objective:</td><td rowspan=1 colspan=1>Allows a logged-in Customer to complete an end-to-end online ticket booking — selecting seats,optionally adding F&amp;B and discounts, and processing payment — resulting in a confirmedbooking and QR code delivery.</td></tr><tr><td rowspan=1 colspan=1>Primary Actor:</td><td rowspan=1 colspan=1>Customer</td></tr><tr><td rowspan=1 colspan=1>Secondary Actor:</td><td rowspan=1 colspan=1>Movie Content Provider (TMDB API)</td></tr><tr><td rowspan=1 colspan=1>Trigger:</td><td rowspan=1 colspan=1>Customer selects a showtime from Movie Detail page (UC-07) and clicks “Đt vé ngay”.</td></tr><tr><td rowspan=1 colspan=1>Pre-condition:</td><td rowspan=1 colspan=1>- Customer is logged in.- Selected showtime has available seats and is not frozen.</td></tr><tr><td rowspan=1 colspan=1>Post-condition:</td><td rowspan=1 colspan=1>- Booking is confirmed with status = CONFIRMED.- Seats are locked and QR e-ticket is generated.- Confirmation email + SMS sent.</td></tr><tr><td rowspan=1 colspan=1>Main Flow:</td><td rowspan=1 colspan=1>1. Customer clicks &quot;Đt vé ngay&quot; on a showtime from Movie Detail page.2. System enters Bưc 1: Chn gh (Seat Map screen) with real-time seat availability and10-minute timer.3. Customer selects seats → System locks them temporarily (CBR-01).4. Customer clicks &quot;Tip tc →&quot; → moves to Bưc 2: Đồ ăn (F&amp;B) (UC-11).5. Customer optionally adds F&amp;B items (or clicks &quot;B qua bưc này&quot;) → clicks &quot;Tip tc→&quot;.</td></tr></table>

<table><tr><td rowspan="6"></td><td rowspan="5">6. System moves to Bưc 3: Voucher &amp; Đim → Customer enters voucher or redeems points (UC-12, UC-25).</td><td></td></tr><tr><td></td></tr><tr><td>7. Customer clicks &quot;Tip tc &quot; → moves to Bưc 4: Thanh toán.</td></tr><tr><td>8. System displays order summary with pricing breakdown.</td></tr><tr><td>9. Customer selects payment method (VNPay, MoMo, Visa) and clicks &quot;Xác nhn &amp; Thanh</td></tr><tr><td rowspan="5"></td><td>toán&quot;.</td></tr><tr><td>10. System processes payment via gateway (UC-13).</td></tr><tr><td>11. Upon successful callback → Booking status = CONFIRMED, QR code generated. 12. System displays Confirmation Screen with QR code, option to &quot;Tåi E-ticket&quot; or &quot;Vë trang</td></tr><tr><td>ch&quot;.</td></tr><tr><td>13. System sends confirmation email + SMS (UC-14). 14. Use case ends successfully.</td></tr><tr><td rowspan="6">Alternative Flow:</td><td></td></tr><tr><td>AF1: Skip F&amp;B – Customer clicks &quot;B qua bưc này&quot; in Step 2 of Booking wizard.</td></tr><tr><td>AF2: Voucher invalid – System shows error, allows retry or skip.</td></tr><tr><td>AF3: Payment fails – Seats released, return to Step 4 of Booking wizard with error message.</td></tr><tr><td>AF4: Voucher discount reduced due to 39% cap – If the combined total of</td></tr><tr><td>Birthday/Friday/Online/Voucher discounts would exceed 39% of the Step 2 price, System automatically reduces the voucher discount amount until the combined total equals exactly</td></tr><tr><td rowspan="8"></td><td>future bookings (BR-UC12-02). EF1: Seat conflict / No available seats Stop at Main Flow step 3. System shows: &quot;Gh bn chn</td></tr><tr><td>đã b đt bi ngưi khác. Vui lòng chn gh khác.&quot;</td></tr><tr><td>EF2: Seat lock timeout Stop during seat selection. System releases locked seats and shows:</td></tr><tr><td>&quot;Thi gian chn gh đã ht. Vui lòng chn li.&quot; EF3: Payment timeout / Failed Stop at payment step. System releases seats and shows</td></tr><tr><td>appropriate error message from gateway. Booking status = FAILED. EF4: Voucher invalid or expired Stop at voucher step. System shows error and allows customer</td></tr><tr><td>to remove or try another code.</td></tr><tr><td>EF5: Insufficient loyalty points Stop at redeem points step. System shows: &quot;Bn không đ đim</td></tr><tr><td>đ đi.&quot; EF6: Age restriction violation (phim K) Stop before payment if checkbox &quot;Tôi xác nhn có ngưi</td></tr><tr><td rowspan="5"></td><td>ln đi cùng&quot; is not ticked for K-rated movie. System blocks proceeding.</td></tr><tr><td>EF7: Showtime no longer available (sold out or frozen) System shows message and redirects</td></tr><tr><td></td></tr><tr><td>back to Movie Detail or showtime list.</td></tr><tr><td></td></tr><tr><td>Business Rules:</td><td>CBR-01, CBR-06, CBR-07, CBR-10</td></tr></table>

3.1.7 UC-10: Select Seats
<table><tr><td colspan="1" rowspan="1">Objective:</td><td colspan="2" rowspan="1">Allows a Customer (online) or Cashier (POS) to view the real-time seat map and select seats forthe chosen showtime. Selected seats are locked for a shared 10-minute session windowpending payment.</td></tr><tr><td colspan="1" rowspan="1">Primary Actor:</td><td colspan="2" rowspan="1">Customer, Cashier</td></tr><tr><td colspan="1" rowspan="1">Secondary Actor:</td><td colspan="2" rowspan="1">None</td></tr><tr><td colspan="1" rowspan="1">Trigger:</td><td colspan="2" rowspan="1">Invoked as &lt;&lt;include&gt;&gt; from UC09 (Step 2) or UC16 (Step 5).</td></tr><tr><td colspan="1" rowspan="1">Pre-condition:</td><td colspan="2" rowspan="1">- An active booking session exists for a specific showtime.- The showtime has at least one Available seat.</td></tr><tr><td colspan="1" rowspan="1">Post-condition:</td><td colspan="2" rowspan="1">- Selected seats = LOCKED.</td></tr><tr><td>Main Flow:</td><td colspan="2">- Shared 10-minute session timer is active (CBR-01).</td></tr><tr><td colspan="2"></td><td>1. System renders the real-time seat map for the selected showtime:</td></tr><tr><td rowspan="7"></td><td>AvailableLocked by others  Sold  Blocked (physical o obstruction).</td></tr><tr><td>Seat type color-coded: For example, seat types are: Standard / VIP / Sweetbox; O price displayed per type.</td></tr><tr><td>2. For POS (Cashier): System displays a phone number lookup field at the top of the screen:</td></tr><tr><td>+ Cashier enters customer's phone number and clicks "Lookup".</td></tr><tr><td>+ System loads the customer's profile (to enable loyalty points accumulation for this booking).</td></tr><tr><td></td></tr><tr><td>3. Actor clicks a seat: o System confirms seat is Available (CBR-03 concurrent conflict check). o System confirms selection does not produce an orphan seat in the row (CBR- 02). System confirms Customer meets age requirement for the film if applicable o (CBR-04). 4. Seat status = LOCKED; shared 10-minute timer continues from the session's first lock (CBR-01). Countdown displayed; red warning at 1 minute remaining.</td></tr><tr><td>Alternative Flow:</td><td>AF1: Actor deselects a previously locked seat: 1. Actor clicks a seat they have already locked in the current session. 2. Seat released back to Available; session timer continues uninterrupted. 3. Actor selects a replacement seat; flow resumes from Step 2.</td></tr><tr><td>Exception Flow:</td><td>EF1: Seat was locked by another user between map render and click (CBR-03)  "This seat is no longer available." Map refreshes; Actor selects an alternative. EF2: Selection would create an orphan seat (CBR-02)  "This selection leaves a single isolated empty seat. Please adjust." Seat not locked. Exception: if ≤ 3 empty seats remain in the row,</td></tr><tr><td></td><td>CBR-02 is waived and the seat locks normally. EF3: 10-minute session timer expires (CBR-01) → all locked seats released simultaneously. "Session expired. Please start again." Actor redirected to showtime selection. EF4: Online Customer attempts to select a 9th seat (BR-UC10-01)  "Maximum 8 seats per</td></tr><tr><td>Business Rules:</td><td>booking." Selection rejected. CBR-01, CBR-02, CBR-03 BR-UC10-01: Max 8 Seats (Online Channel): A Customer may select a maximum of 8 seats in a single online booking session. Attempting a 9th seat is rejected immediately. This restriction does not apply to Cashier POS sessions.</td></tr></table>

3.1.8 UC-11: Pre-order Food & Beverage
<table><tr><td colspan="1" rowspan="1">Objective:</td><td colspan="2" rowspan="1">Allows a Customer to add F&amp;B items to an in-progress booking before payment. Available onlywhen the showtime begins more than 30 minutes from the time of ordering.</td></tr><tr><td colspan="1" rowspan="1">Primary Actor:</td><td colspan="2" rowspan="1">Customer</td></tr><tr><td colspan="1" rowspan="1">Secondary Actor:</td><td colspan="2" rowspan="1">None</td></tr><tr><td colspan="1" rowspan="1">Trigger:</td><td colspan="2" rowspan="1">Invoked as &lt;&lt;extend&gt;&gt; from UC09 (Step 4) when Customer chooses to add F&amp;B.</td></tr><tr><td colspan="1" rowspan="1">Pre-condition:</td><td colspan="2" rowspan="1">- Active UC09 booking session exists.- showtime_start – server_time &gt; 30 minutes (BR-UC11-01); if not met, UC11 is not invoked.</td></tr><tr><td colspan="1" rowspan="1">Post-condition:</td><td colspan="2" rowspan="1">- F&amp;B items appended to booking cart.- UC09 order total updated to include F&amp;B subtotal.</td></tr><tr><td></td><td colspan="2">- Shared 10-minute session timer is active (CBR-01).</td></tr><tr><td>Main Flow:</td><td>&amp; Snack, Đồ ung). 3. System updates running F&amp;B subtotal on the right panel. 4. Customer clicks "Tip tc →" (or "B qua bưc này") 5. Selected F&amp;B items are added to the booking cart. 6. System proceeds to UC-12 (Voucher &amp; Đim).</td><td>1. System displays Bưc 2: Đồ ăn in booking wizard with category tabs (Combo, Bng ngô 2. Customer browses and selects items, adjusts quantities (+/-).</td></tr><tr><td>Alternative Flow:</td><td></td><td>AF1: Skip F&amp;B Customer clicks "B qua buc này"  No F&amp;B added, proceeds to next</td></tr><tr><td>Exception Flow:</td><td>step. entirely; UC11 is not invoked. UC09 proceeds to Step 5.</td><td>EF1: showtime_start – server_time ≤ 30 min at invocation (BR-UC11-01) → F&amp;B step hidden EF2: An item becomes UNAVAILABLE after the menu loads → greyed out in real time. Customer</td></tr><tr><td>Business Rules:</td><td>removes it before confirming. is hidden and UC11 is not triggered. success. Once CONFIRMED, they are excluded from all refund calculations under any</td><td>BR-UC11-01: Food Order Cutoff: UC11 is accessible only when showtime_start – server_time &gt; 30 minutes (evaluated using server time at invocation). If this condition is not met, the F&amp;B step BR-UC11-02: Food Non-Refundable: F&amp;B items are marked CONFIRMED upon booking payment</td></tr></table>

3.1.9 UC-12: Apply Voucher Or Promotion Code
<table><tr><td>Objective:</td><td>Allows a Customer (online) or Cashier (POS) to enter and apply a single voucher code as a Tier 3 discount against the ticket subtotal of an in-progress booking</td></tr><tr><td>Primary Actor: Secondary Actor:</td><td>Customer (Online), Cashier (Offline)</td></tr><tr><td>Trigger:</td><td>None Invoked as &lt;&lt;extend&gt;&gt; from UC09 (Step 5) or UC16 (Step 8) when Actor chooses to apply a</td></tr><tr><td></td><td>code.</td></tr><tr><td>Pre-condition:</td><td>- Active checkout session with at least one ticket item.</td></tr><tr><td></td><td>- No more than one voucher code currently active (CBR-11).</td></tr><tr><td>Post-condition:</td><td>- Valid voucher discount applied to ticket subtotal per CBR-10 and CBR-11. - Order total updated.</td></tr><tr><td>Main Flow:</td><td>1. System displays the voucher input section: 1. Online (Customer): In Bưóc 3: Voucher &amp; Đim. 2. POS (Cashier): In F&amp;B &amp; Voucher screen.</td></tr><tr><td></td><td>2. Actor enters voucher code in the input field. 3. Actor clicks "Áp dng" (Online) or "Apply" (POS). 4. System validates the code against all CBR-12 conditions. 5.</td></tr><tr><td></td><td>If valid, system displays the applied voucher with discount amount and updates the order summary in real-time. 6. Actor continues with the flow:</td></tr><tr><td></td><td>1. Online: Can also adjust loyalty points using slider before clicking "Tip tc →". 2. POS: Proceeds to next step (Payment).</td></tr><tr><td>Alternative Flow:</td><td>7. Use case ends successfully.</td></tr><tr><td></td><td>AF1: Remove voucher Customer clicks X on applied voucher → discount is removed,</td></tr><tr><td></td><td>total updated.</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td>Exception Flow:</td><td></td></tr><tr><td></td><td>EF1: Any CBR-12 condition fails → specific error message displayed per the failing condition (see</td></tr><tr><td></td><td>CBR-12); code not applied. Actor may enter a different code.</td></tr><tr><td></td><td>EF2: Actor modifies the order (changes seat or showtime) after applying the voucher  voucher</td></tr><tr><td></td><td>re-validated at payment confirmation (CBR-12). If no longer eligible → Actor warned; must</td></tr><tr><td>Business Rules:</td><td>remove or replace code before payment proceeds.</td></tr><tr><td></td><td>CBR-11, CBR-12 BR-UC12-01: Voucher:</td></tr><tr><td></td><td>Partial Cap Handling — If the 39% discount cap (CBR-11) is reached before the voucher discount</td></tr><tr><td></td><td>is applied, the voucher code is NOT marked as used and remains valid for future bookings.</td></tr><tr><td></td><td>System displays a notice: "Voucher ca bn không th áp dng do đt ch này đã đt gii hn</td></tr><tr><td></td><td>gim giá ti đa."</td></tr><tr><td>3.1.10 UC-13: Process Online Payment</td><td></td></tr><tr><td>Objective:</td><td>Processes the payment for a confirmed online booking order through the selected external</td></tr><tr><td></td><td>payment gateway and updates booking status based on the gateway response.</td></tr><tr><td></td><td></td></tr><tr><td>Primary Actor:</td><td>Customer, Cashier</td></tr><tr><td>Secondary Actor:</td><td>Payment Gateway</td></tr><tr><td>Trigger:</td><td>Invoked as &lt;&lt;include&gt;&gt; from UC09 (Step 4 in booking wizard) after Customer selects a payment</td></tr><tr><td></td><td>method and confirms the order. Pre-condition:</td></tr><tr><td>Pre-condition:</td><td>- Booking = PENDING_PAYMENT.</td></tr><tr><td></td><td>- At least one seat locked; total amount calculated (at the moment first seat is locked).</td></tr><tr><td>Post-condition:</td><td>- Booking status = CONFIRMED (SUCCESS), FAILED (gateway FAIL), or EXPIRED (timeout).</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>1. System displays Bưóc 4: Thanh toán with full order summary on the left.</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td>Main Flow:</td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">6. Upon SUCCESS callback → Booking = CONFIRMED, proceeds to UC-14.</td></tr><tr><td colspan="1" rowspan="1">Alternative Flow:</td><td colspan="1" rowspan="1">1. Customer closes the active gateway interface (e.g., closes MoMo window).2. Customer selects a different payment method from the order summary page.3. System re-initiates the gateway flow for the new method; Booking remainsPENDING_PAYMENT; 15-minute timer continues from its original start (CBR-06).4. Customer completes transaction → SUCCESS → Booking = CONFIRMED.</td></tr><tr><td colspan="1" rowspan="1">Exception Flow:</td><td colspan="1" rowspan="1">EF1: Gateway returns FAIL callback within the window  Booking = FAILED; seats released;gateway error reason displayed. Customer may retry with a different method if time permits.EF2: No gateway callback within 15 minutes (CBR-06) → Booking = EXPIRED; seats released."Payment session expired. Please start a new booking."</td></tr><tr><td colspan="1" rowspan="1">Business Rules:</td><td colspan="1" rowspan="1">CBR-06</td></tr></table>

## Post-Booking

3.1.11 UC-14: Receive Booking Confirmation and QR Code
<table><tr><td rowspan=1 colspan=1>Objective:</td><td rowspan=1 colspan=1>Automatically triggered upon booking confirmation to generate a unique HMAC-signed QR codeand deliver confirmation details to the Customer via email and SMS.</td></tr><tr><td rowspan=1 colspan=1>Primary Actor:</td><td rowspan=1 colspan=1>Customer (passive)</td></tr><tr><td rowspan=1 colspan=1>Secondary Actor:</td><td rowspan=1 colspan=1>Email Service, SMS Service</td></tr><tr><td rowspan=1 colspan=1>Trigger:</td><td rowspan=1 colspan=1>&lt;&lt;trigger&gt;&gt; from UC09 (Step 10) or UC17 (Step 2) when a booking reaches CONFIRMED status.</td></tr><tr><td rowspan=1 colspan=1>Pre-condition:</td><td rowspan=1 colspan=1>- Booking has just reached CONFIRMED status.</td></tr><tr><td rowspan=1 colspan=1>Post-condition:</td><td rowspan=1 colspan=1>- QR code generated and persisted against the booking record.- Customer has received confirmation email and SMS.- Automated showtime reminder scheduled.</td></tr><tr><td rowspan=1 colspan=1>Main Flow:</td><td rowspan=1 colspan=1>1. System generates unique HMAC-signed QR code (CBR-14).2. System displays Confirmation Screen with large QR code, booking details, seats, F&amp;B,and total.3. System provides buttons: &quot;Ti E-ticket&quot; and &quot;Vê trang ch&quot;.4. Email Service sends detailed confirmation email (ET-05) with QR attached.5. SMS Service sends summary SMS. This message include a note message: &quot;Vé ca bn ápdng ưu đãi Hc sinh/Sinh viên. Vui lòng mang theo CCCD hoc thė Hc sinh/Sinh viênkhi đn rp đ xut trình khi đưc yêu cu.&quot; if they are applied student discount (age &lt;= 22)6. Use case ends successfully.</td></tr><tr><td rowspan=1 colspan=1>Alternative Flow:</td><td rowspan=1 colspan=1>None</td></tr><tr><td rowspan=1 colspan=1>Exception Flow:</td><td rowspan=1 colspan=1>EF1: Email delivery fails → system retries up to 3 times with exponential backoff; failure logged.Booking remains CONFIRMED; QR code accessible via UC15.EF2: SMS delivery fails (Step 3) → failure logged. No retry. Booking remains CONFIRMED.Customer can access QR code and booking details via UC-15. SMS is a supplementary channel —booking validity is not affected</td></tr><tr><td rowspan=1 colspan=1>Business Rules:</td><td rowspan=1 colspan=1>CBR-14 (QR code contains booking_id + HMAC-SHA256 signature; single-use; validated at check-in in UC19)</td></tr></table>

3.1.12 UC-15: View Booking History & E-Ticket
<table><tr><td colspan="1" rowspan="1">Objective:</td><td colspan="2" rowspan="1">Allows a Customer to browse their full booking history across Upcoming, Past, and Cancelledtabs, view e-ticket QR codes, and initiate cancellation for eligible online bookings.</td></tr><tr><td colspan="1" rowspan="1">Primary Actor:</td><td colspan="2" rowspan="1">Customer</td></tr><tr><td colspan="1" rowspan="1">Secondary Actor:</td><td colspan="2" rowspan="1">None</td></tr><tr><td colspan="1" rowspan="1">Trigger:</td><td colspan="2" rowspan="1">Customer navigates to My Account → Lch s đt vé</td></tr><tr><td colspan="1" rowspan="1">Pre-condition:</td><td colspan="2" rowspan="1">- Customer is logged in.</td></tr><tr><td colspan="1" rowspan="1">Post-condition:</td><td colspan="2" rowspan="1">- Booking status = CONFIRMED (SUCCESS), FAILED (gateway FAIL), or EXPIRED (timeout).- Customer has viewed booking details and QR codes.</td></tr><tr><td></td><td colspan="2"></td></tr><tr><td>Main Flow:</td><td rowspan="6"></td><td>1. Customer goes to Profile and selects "Lch s đt vé". 2. System displays three tabs: Såp chiu, Đã xem, Đã hu.</td></tr><tr><td>3. Default tab is Såp chiu.</td><td>4. Each booking card shows: Movie poster, title, showtime, room, seats, total amount, status badge (CONFIRMED, CHECKED_IN, CANCELLED...).</td></tr><tr><td>vé".</td><td>5. Customer clicks "Xem QR" on a booking card  System displays large QR code + booking details (matches Confirmation screen style). 6. For eligible bookings (Upcoming + within cancellation window), Customer can click "Hu</td></tr><tr><td>Alternative Flow:</td><td>7. Use case ends successfully.</td></tr><tr><td>Exception Flow:</td><td>AF1: View Past/Cancelled – Customer switches tab to see history.</td></tr><tr><td>None Business Rules: CBR-08</td><td></td></tr></table>

## Offline Box Office Operations

## 3.1.13 UC-16: Sell Tickets at Box Office (Walk-in)

<table><tr><td>Objective:</td><td>Allows a Cashier to process a walk-in ticket purchase via POS — selecting a showtime and seats,</td></tr><tr><td></td><td>applying optional F&amp;B items and discounts, and confirming the order for counter payment.</td></tr><tr><td>Primary Actor:</td><td>Cashier</td></tr><tr><td>Secondary Actor:</td><td>None</td></tr><tr><td>Trigger:</td><td>Customer approaches the box office; Cashier opens a new sale in the POS system.</td></tr><tr><td>Pre-condition:</td><td>- Cashier is logged into POS.</td></tr><tr><td></td><td>- Selected showtime is within the permitted sales window (CBR-09).</td></tr><tr><td>Post-condition:</td><td>- Offline order confirmed; UC17 invoked for payment processing.</td></tr><tr><td>Main Flow:</td><td>1. Cashier navigates to "Select Movie &amp; Showtime" screen and selects a movie and showtime.</td></tr><tr><td></td><td>2. System validates the showtime sales window (CBR-09). 3.</td></tr><tr><td></td><td>System checks film rating (CBR-04): For restricted movies, Cashier verifies customer's ID/guardian and records ageverified = true + verifiedBy = cashier_id.</td></tr><tr><td></td><td>4. Cashier enters customer's phone number and clicks "Lookup" to load customer profile</td></tr><tr><td></td><td>(for loyalty points).</td></tr><tr><td></td><td>5. &lt;&lt;include&gt;&gt; UC-10 — System displays real-time seat map. Cashier selects seats (no seat limit for POS).</td></tr><tr><td></td><td>6. Cashier proceeds to F&amp;B &amp; Voucher screen (optional but recommended):</td></tr><tr><td></td><td>o Adds F&amp;B items (UC-11). Optionally enters and applies voucher code (UC-12).</td></tr><tr><td></td><td>7. System automatically applies eligible promotions (Birthday discount via verifiedDob,</td></tr><tr><td></td><td>Student discount after manual verification)</td></tr><tr><td></td><td>8. System displays full Order Summary.</td></tr><tr><td></td><td>9. Cashier confirms the order with the customer.</td></tr><tr><td></td><td>10. System proceeds to Process Payment (UC-17).</td></tr><tr><td></td><td>11. After successful payment, system automatically goes to Print Tickets &amp; Receipt (UC-18). 12. Use case ends successfully.</td></tr><tr><td></td><td></td></tr><tr><td>Alternative Flow:</td><td>AF1: No registered account found for walk-in customer (Step 4):</td></tr><tr><td></td><td>1. Phone number and membership ID lookup return no match.</td></tr><tr><td></td><td>2. Cashier proceeds without account linking.</td></tr><tr><td></td><td>3. Booking created with source = OFFLINE, account_id = NULL; no loyalty points</td></tr><tr><td></td><td>credited. 4. All remaining steps (5–9) proceed unchanged.</td></tr><tr><td></td><td></td></tr><tr><td>Exception Flow:</td><td>EF1: Showtime started &gt; 15 minutes ago (CBR-09 grace expired)  "Sales are closed for this</td></tr><tr><td></td><td>showtime." POS blocks further action. Flow ends.</td></tr><tr><td></td><td>EF2: Customer cannot provide valid ID for T-rated film (CBR-04) → Cashier must decline</td></tr><tr><td></td><td>booking. Flow ends.</td></tr><tr><td></td><td>EF3: Seat conflict during selection — seat just locked by an online customer (CBR-03) → POS</td></tr><tr><td></td><td>map refreshes; Cashier selects an alternative seat.</td></tr><tr><td></td><td></td></tr><tr><td></td><td>EF4: Seat selection creates orphan (CBR-02) → warning displayed; Cashier adjusts selection.</td></tr><tr><td></td><td>Exception: ≤ 3 empty seats remain in row → rule waived.</td></tr><tr><td></td><td>EF5: Customer cancels the purchase mid-transaction (User Choice)</td></tr><tr><td></td><td>1. At any point before confirming the order (Step 10), the customer decides not to proceed with the booking. 2. Cashier clicks the [Cancel Sale] button on the POS interface. 3. System automatically releases any locked seats (from UC10) to the real-time pool and clears the current pending transaction session. 4. POS screen resets to the initial movie selection dashboard. Flow ends.</td></tr><tr><td>Business Rules:</td><td>CBR-01, CBR-12 BR-UC16-01: Minimum Occupancy Requirement A showtime may only be sold at the box office if the total number of CONFIRMED tickets for that showtime — including the seat(s) in the current transaction — reaches at least 2. The system calculates this as: (existing confirmed bookings for the showtime, online + offline) + (seats being purchased in this transaction). If the resulting total is less than 2, the sale is blocked and the Cashier is shown a warning.</td></tr></table>

3.1.14 UC-17: Process Counter Payment
<table><tr><td>Objective:</td><td>Allows a Cashier to collect payment from a walk-in customer via card or cash or transferring through QR, create the confirmed offline booking record, and trigger ticket printing.</td></tr><tr><td>Primary Actor:</td><td>Cashier</td></tr><tr><td>Secondary Actor:</td><td>None</td></tr><tr><td>Trigger:</td><td>Invoked as &lt;&lt;include&gt;&gt; from UC16 (Step 9) after order is confirmed</td></tr><tr><td>Pre-condition:</td><td>- Walk-in order confirmed in UC16; total amount calculated.</td></tr><tr><td>Post-condition:</td><td>- Booking = CONFIRMED (source = OFFLINE).</td></tr><tr><td></td><td>- Loyalty points credited if booking is linked to a Customer account.</td></tr><tr><td></td><td>- UC18 invoked.</td></tr><tr><td>Main Flow:</td><td>1. System displays Process Payment screen with order summary on the right. 2. Cashier selects payment method: o Cash</td></tr><tr><td></td><td> Card (POS terminal)</td></tr><tr><td></td><td>0 QR Transfer 3. If Cash: Cashier enters amount tendered  System calculates and displays change due.</td></tr><tr><td></td><td>4. If Card: Cashier processes payment via POS terminal.</td></tr><tr><td></td><td>5. If QR Transfer: System generates dynamic QR code with Booking ID and total amount.</td></tr><tr><td></td><td>6. Cashier confirms successful payment.</td></tr><tr><td></td><td>7. System creates Booking record (status = CONFIRMED, source = OFFLINE).</td></tr><tr><td></td><td>8. If customer is linked  loyalty points are credited.</td></tr><tr><td></td><td>9. &lt;&lt;include&gt;&gt; UC-18 — Print tickets and receipt.</td></tr><tr><td></td><td>10. Use case ends successfully.</td></tr><tr><td></td><td></td></tr><tr><td>Alternative Flow:</td><td>AF1: Customer pays cash:</td></tr><tr><td></td><td>1. Cashier selects Cash as payment method.</td></tr><tr><td></td><td>2. Cashier enters amount tendered → system calculates and displays change due.</td></tr><tr><td></td><td>3. Cashier confirms → Booking = CONFIRMED. Flow continues at Step 3</td></tr><tr><td></td><td></td></tr><tr><td></td><td>AF2: Customer pays via QR Code (Bank Transfer / E-Wallet):</td></tr><tr><td></td><td>1. Cashier selects QR Payment as the payment method.</td></tr><tr><td></td><td>2. System generates a dynamic QR code containing the Booking_ID and exact</td></tr><tr><td></td><td>total_amount, then displays it on the customer-facing screen.</td></tr><tr><td></td><td>3. Customer scans the QR code and completes the payment via their Mobile Banking or E-Wallet app.</td></tr><tr><td></td><td>4. System listens to the payment gateway webhook/callback:</td></tr><tr><td></td><td>0 If callback = SUCCESS =&gt; Booking status updated to CONFIRMED. Flow</td></tr><tr><td></td><td>continues at Main Flow Step 3.</td></tr><tr><td></td><td>If 3 minutes pass without a successful callback =&gt; System displays a o</td></tr><tr><td></td><td>"Timeout/Pending" warning. Cashier can click "Re-verify" or switch</td></tr><tr><td></td><td></td></tr><tr><td></td><td>payment method.</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td>Exception Flow:</td><td>EF1: Card DECLINED by POS terminal → "Card payment declined." Cashier offers alternative payment method. Booking not created until payment succeeds. EF2 (applies to AF1): Cash tendered is less than total due → POS displays shortfall amount; Cashier requests correct amount from customer.</td></tr><tr><td>Business Rules:</td><td>None</td></tr></table>

3.1.15 UC-18: Print Physical Ticket & Receipt
<table><tr><td rowspan=1 colspan=1>Objective:</td><td rowspan=1 colspan=1>Generates and prints a physical ticket for each booked seat and an itemized payment receipt forthe walk-in customer.</td></tr><tr><td rowspan=1 colspan=1>Primary Actor:</td><td rowspan=1 colspan=1>Cashier</td></tr><tr><td rowspan=1 colspan=1>Secondary Actor:</td><td rowspan=1 colspan=1>None</td></tr><tr><td rowspan=1 colspan=1>Trigger:</td><td rowspan=1 colspan=1>Invoked as &lt;&lt;include&gt;&gt; from UC17 (Step 4) after booking reaches CONFIRMED status.</td></tr><tr><td rowspan=1 colspan=1>Pre-condition:</td><td rowspan=1 colspan=1>- Booking = CONFIRMED (source = OFFLINE).</td></tr><tr><td rowspan=1 colspan=1>Post-condition:</td><td rowspan=1 colspan=1>- Physical ticket(s) printed (one per seat) and handed to customer.- Receipt printed and handed to customer.</td></tr><tr><td rowspan=1 colspan=1>Main Flow:</td><td rowspan=1 colspan=1>1. System generates ticket data for each booked seat (movie, showtime, room, seatnumber, QR code with HMAC signature).2. Cashier clicks &quot;Print tickets &amp; receipt&quot;.3. System sends:o One physical ticket per seat to thermal printer (with QR code).o One itemized receipt (tickets + F&amp;B + discounts + payment method).4. Cashier hands tickets and receipt to customer.5. Use case ends successfully.</td></tr><tr><td rowspan=1 colspan=1>Alternative Flow:</td><td rowspan=1 colspan=1>None</td></tr><tr><td rowspan=1 colspan=1>Exception Flow:</td><td rowspan=1 colspan=1>EF1: Printer offline or paper jam  error displayed on POS. Cashier resolves hardware issue andretries. Booking remains CONFIRMED; reprinting is permitted at any time.</td></tr><tr><td rowspan=1 colspan=1>Business Rules:</td><td rowspan=1 colspan=1>None</td></tr></table>

<table><tr><td>- Item - - Amount - Movie Ticket: Avengers 2 @120,000 VND 240,000 VND Popcorn (Large) 1 @ 80,000 VND 80,000 VND Soda (Medium) 2 @ 40,000 VND 80,000 VND Nachos 1 @ 90,000 VND 90,000 VND</td></tr></table>

Demo printed Itemised receipt and Physical ticket

# CINEMA STAR

123 Star Plaza, Hanoi, Vietnam (or a placeholder for local details) (024) 555-0199

01/10/2025 19:15:33

## EMPLOYEE REIMBURSEMENT INVOICE

![](images/7d5b1d9d348130ccd2aa0bc82a7d87cbcb2a71c7b2051313ae7922faaeeea071.jpg)

## Check-in & Concession

3.1.16 UC-19: Check-in via QR Code Scan
<table><tr><td colspan="1" rowspan="1">Objective:</td><td colspan="1" rowspan="1">Allows a Cashier to scan a customer's booking QR code at the cinema entrance, validate thebooking against security conditions, and mark the booking as CHECKED_IN.</td></tr><tr><td colspan="1" rowspan="1">Primary Actor:</td><td colspan="1" rowspan="1">Cashier</td></tr><tr><td colspan="1" rowspan="1">Secondary Actor:</td><td colspan="1" rowspan="1">None</td></tr><tr><td colspan="1" rowspan="1">Trigger:</td><td colspan="1" rowspan="1">Customer presents a booking QR code (mobile screen or printed ticket) at the cinema entrance.Cashier clicks "Scan QR Check-in" button from any POS screen (e.g. Showtimes screen) orchoose QR Check-in tab on navigation bar</td></tr><tr><td colspan="1" rowspan="1">Pre-condition:</td><td colspan="1" rowspan="1">- Cashier is logged into POS with a QR scanning device connected.- Booking exists in the system.</td></tr><tr><td colspan="1" rowspan="1">Post-condition:</td><td colspan="1" rowspan="1">- Booking status = CHECKED_IN.- If the booking has an associated F&amp;B order, UC20 is triggered.</td></tr><tr><td colspan="1" rowspan="1">Main Flow:</td><td colspan="1" rowspan="1">Main Flow:1. Customer presents QR code.2. Cashier scans QR code using scanner or camera.3. System validates QR (CBR-14): signature, status = CONFIRMED, correct date, notyet checked in.4. Cashier performs visual verification:</td></tr><tr><td></td><td>For T-rated / K-rated movies: Check ID / guardian presence. o For Student discount (if claimed): Verify student ID if needed. 5. All validations pass → System sets status = CHECKED IN and invalidates QR. 6. System shows confirmation screen with booking details. 7. If F&amp;B order exists → Notify Concession Staff (UC-20). 8. Use case ends successfully.</td></tr><tr><td>Alternative Flow:</td><td>AF1: Printed ticket – Cashier scans barcode/QR on printed ticket (same flow).</td></tr><tr><td>Exception Flow:</td><td>EF1: Digital signature invalid or tampered (CBR-14) → “Invalid QR code." Entry denied. EF2: Booking status is not CONFIRMED, e.g. CANCELLED or EXPIRED (CBR-14) →“This</td></tr><tr><td></td><td>booking is not valid for check-in. Status: [status]." Entry denied. EF3: Showtime date does not match today (CBR-14)  “This ticket is not valid for</td></tr><tr><td></td><td>today's showtime." Entry denied. EF4: Booking has already been checked in (CBR-14) →"This ticket has already been</td></tr><tr><td></td><td>used at [check-in time]." Entry denied.</td></tr><tr><td></td><td>EF5: Customer cannot prove the minimum required age for a T13/T16/T18 film (no valid ID or ID shows underage): 1. Cashier denies entry and explains the reason to the customer.</td></tr><tr><td></td><td>2. System displays an error message on the POS screen: "Entry denied — minimum age requirement not met. Your ticket will be cancelled and the ticket price will be refunded 100%. As your F&amp;B order has been paid for and is non-refundable (per BR-UC11-02), please proceed to the Concession counter to collect your order. The kitchen has been notified to prepare it."</td></tr><tr><td></td><td>3. Cashier clicks "[Deny Check-in]" button on the interface. 4. System &lt;&lt;triggers&gt;&gt; UC-22: Handle Ticket Issue with parameter refund_reason = AGEDENIAL to execute the 100% ticket refund process according to CBR-05. 5. System marks the ticket portion as cancelled/refunded, but keeps the F&amp;B order</td></tr><tr><td></td><td>as CONFIRMED. 6. System &lt;&lt;triggers&gt;&gt; UC-20 (F&amp;B fulfillment) for this booking immediately so Concession Staff can prepare and hand over the food. Entry to the theater remains denied.</td></tr><tr><td></td><td>EF6: Customer cannot present a valid student/school ID:</td></tr><tr><td></td><td>1. Cashier requests the customer to pay the price difference via Counter Payment. 2. If the customer pays the difference: Cashier processes the payment, System updates the booking, and flow returns to Main Flow Step 5 (Entry allowed).</td></tr><tr><td></td><td>3. If the customer refuses to pay the difference: Cashier denies check-in. 4. Cashier clicks "[Deny Check-in]" button on the interface.</td></tr><tr><td></td><td></td></tr><tr><td></td><td>5. System &lt;&lt;triggers&gt;&gt; UC-22: Handle Ticket Issue with parameter refund_reason = ID_VERIFICATION_FAILED to execute the 100% ticket refund process according to CBR-05. 6. System marks the ticket portion as cancelled/refunded, keeps the F&amp;B order as</td></tr><tr><td></td><td>CONFIRMED, and &lt;&lt;triggers&gt;&gt; UC-20 for F&amp;B collection. Entry to the theater is denied.</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>EF7: For a K-rated film, the child is not accompanied by a guardian aged ≥18, or the</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>guardian cannot present a valid government-issued ID to prove their age → Cashier</td></tr><tr><td></td><td></td></tr><tr><td></td><td>denies entry for the whole group.</td></tr><tr><td></td><td></td></tr><tr><td></td><td>“Entry denied — children under 13 must be accompanied by an adult guardian (≥18</td></tr><tr><td></td><td></td></tr><tr><td></td><td>years old) with valid ID. Your tickets will be cancelled and the ticket price refunded</td></tr><tr><td></td><td></td></tr><tr><td>notified to prepare it." this booking immediately, so Concession Staff can prepare and hand over the food.</td><td>100%. As your F&amp;B order has been paid for and is non-refundable (per BR-UC11-02), please proceed to the Concession counter to collect your order. The kitchen has been System action: Booking ticket portion is cancelled and refunded per CBR-04 exception. The F&amp;B order remains CONFIRMED. System &lt;&lt;triggers&gt;&gt; UC-20 (F&amp;B fulfillment) for</td></tr></table>

3.1.17 UC-20: Fulfill Food Pre-order at Concession
<table><tr><td>Objective:</td><td>Allows Concession Staff to receive and fulfill F&amp;B pre-orders associated with a booking, triggered conditionally upon successful QR code check-in when an F&amp;B order exists.</td></tr><tr><td>Primary Actor:</td><td>Concession Staff</td></tr><tr><td colspan="1" rowspan="1">Secondary Actor:</td><td colspan="1" rowspan="1">None</td></tr><tr><td colspan="1" rowspan="1">Trigger:</td><td colspan="1" rowspan="1">&lt;&lt;trigger&gt;&gt; from UC19 (Step 7) when a checked-in booking has an associated F&amp;B order.</td></tr><tr><td colspan="1" rowspan="1">Pre-condition:</td><td colspan="1" rowspan="1">Booking has just transitioned to CHECKED_IN status with at least one F&amp;B item in PENDINGstatus.</td></tr><tr><td colspan="1" rowspan="1">Post-condition:</td><td colspan="1" rowspan="1">F&amp;B order status = FULFILLED.</td></tr><tr><td colspan="1" rowspan="1">Main Flow:</td><td colspan="1" rowspan="1">1. Concession Display automatically receives and shows the new order in thepending queue.2. System displays all pending F&amp;B orders sorted by check-in time (FIFO), showing:0Booking ID, showtime, seats, check-in time, waiting duration.List of F&amp;B items with quantities.3. Concession Staff prepares the items.4. When ready, Concession Staff hands the order to the customer.5. Concession Staff clicks "Complete" (green button) for full fulfillment, or "Partial"(brown button) if any item is unavailable.6. System updates the F&amp;B order status to FULFILLED or PARTIAL_FULFILLED.7. Use case ends successfully.</td></tr><tr><td colspan="1" rowspan="1">Alternative Flow:</td><td colspan="1" rowspan="1">AF1: Multiple F&amp;B orders are queued simultaneously:1. Concession Staff views the queue sorted by check-in time (FIFO) and processesorders in arrival order, following Steps 2–5 for each.</td></tr><tr><td colspan="1" rowspan="1">Exception Flow:</td><td colspan="1" rowspan="1">EF1: An item becomes unavailable at preparation time (e.g., out of stock) → ConcessionStaff flags the order as “Partial Fulfillment" with a note on the substituted or missingitem; the order is still marked FULFILLED. No automatic refund is triggered, since F&amp;Bitems are non-refundable once CONFIRMED (BR-UC11-02).</td></tr><tr><td colspan="1" rowspan="1">Business Rules:</td><td colspan="1" rowspan="1">None</td></tr></table>

3.1.18 UC-21: Manage F&B Menu
<table><tr><td>Objective:</td><td>Allows the Cinema Manager to manage the concession (F&amp;B) menu including adding new items, editing details, setting prices, categories, images, and availability status for use across online and POS ordering flows.</td></tr><tr><td>Primary Actor:</td><td>Cinema Manager</td></tr><tr><td>Secondary Actor:</td><td>None</td></tr><tr><td>Trigger:</td><td>Cinema Manager navigates to F&amp;B Menu from the left sidebar.</td></tr><tr><td>Pre-condition:</td><td>Manager is logged in.</td></tr><tr><td>Post-condition:</td><td>F&amp;B menu items are updated and immediately reflected in customer booking flows (UC-11) and POS (UC-16).</td></tr><tr><td>Main Flow:</td><td>Main Flow:</td></tr><tr><td></td><td>1. Cinema Manager clicks "F&amp;B Menu" in the left sidebar. 2. System displays the F&amp;B menu grid with filter tabs: All, Popcorn, Drinks, Combos.</td></tr><tr><td></td><td>3. Each item card shows: image, name, category, price, and status badge (Available / Out of stock).</td></tr><tr><td></td><td>4. Manager clicks "+ Add item" to create a new F&amp;B item.</td></tr><tr><td></td><td>5. Manager fills in item details: Name, Description, Price, Category, Image (upload), VAT (if applicable), and Status.</td></tr><tr><td></td><td>6. Manager clicks Save  new item appears immediately in the live menu. 7. To edit, Manager clicks "Edit" on any item card, updates information, and saves</td></tr><tr><td></td><td>changes. 8. Use case ends successfully.</td></tr><tr><td>Alternative Flow:</td><td>AF1: Change Item Availability: Manager toggles an item's status to Out of stock (soft disable). The item remains in the system but is hidden from customer/POS ordering while preserving historical order references.</td></tr><tr><td>Exception Flow:</td><td>EF1: Price is zero, negative, or invalid  “Price must be a positive number." EF2: Required fields (Name, Category, Price) are missing → “[Field] is required."</td></tr><tr><td></td><td></td></tr><tr><td>Business Rules:</td><td>CBR-17 BR-UC21-01: Soft Delete / Availability — F&amp;B items are never hard-deleted. Items are</td></tr><tr><td></td><td>only set to Unavailable / Out of stock to maintain referential integrity for past orders.</td></tr></table>

## Cancellation & Refund

## 3.1.19 UC-22: Cancel Booking

<table><tr><td>Objective:</td><td>Allows a Customer (online) or Cashier (at counter) to cancel an eligible confirmed booking and initiate the refund calculation process based on the time-based refund policy.</td></tr><tr><td>Primary Actor:</td><td>Customer, Cashier</td></tr><tr><td>Secondary Actor:</td><td>None</td></tr><tr><td>Trigger:</td><td>Customer clicks “Cancel” on an eligible booking in UC15, or Cashier initiates a cancellation at</td></tr><tr><td></td><td>the counter on behalf of a walk-in customer.</td></tr><tr><td>Pre-condition:</td><td>- Booking status = CONFIRMED.</td></tr><tr><td></td><td>- Showtime has not yet started (CBR-09).</td></tr><tr><td></td><td>- If cancelling online, booking source = ONLINE (CBR-08).</td></tr><tr><td>Post-condition:</td><td>- Booking status = CANCELLED.</td></tr><tr><td></td><td>- Seats released immediately back to Available.</td></tr><tr><td></td><td>- Refund amount calculated; UC23 triggered.</td></tr><tr><td></td><td>- Loyalty points reversed per CBR-13.</td></tr><tr><td>Main Flow (POS):</td><td>Main Flow (POS - Cashier):</td></tr><tr><td></td><td>1. Cashier navigates to Cancel tab in POS. 2. Buóc 1: Find booking — Cashier enters Booking ID / Phone number / QR scan to</td></tr><tr><td></td><td>load the booking. 3. Buóc 2: Cancel type — Cashier selects reason for cancellation.</td></tr><tr><td></td><td>4. Bưóc 3: Refund calc — System calculates refund percentage based on time to showtime (CBR-05), displays breakdown (ticket refund, F&amp;B non-refundable,</td></tr><tr><td></td><td>loyalty points to be reversed). 5. Cashier reviews and confirms cancellation.</td></tr><tr><td></td><td>6. System sets booking status = CANCELLED, releases seats immediately.</td></tr><tr><td></td><td>7. System triggers UC-23: Process Refund. 8. Use case ends successfully.</td></tr><tr><td>Main Flow (Online)</td><td>Main Flow (Online - Customer):</td></tr><tr><td></td><td>1. Customer goes to Booking History → selects eligible booking → clicks &quot;Hy vé&quot;. 2. System shows cancellation summary with refund amount (CBR-05).</td></tr><tr><td></td><td>3. Customer confirms → Booking = CANCELLED, seats released. 4. System triggers UC-23 (Process Refund).</td></tr><tr><td>Alternative Flow:</td><td>AF1: Partial cancellation (POS only) — Cashier can cancel specific seats instead of whole</td></tr><tr><td></td><td>booking.</td></tr><tr><td>Exception Flow:</td><td>EF1: Cancellation not allowed (showtime started or policy violated) → System shows reason and blocks action.</td></tr><tr><td></td><td>EF2: 0% refund → System warns “Không hoàn li tiên&quot; but still allows cancellation with</td></tr><tr><td></td><td>points reversal.</td></tr><tr><td></td><td></td></tr></table>

## 3.1.20 UC-23: Process Refund

<table><tr><td colspan="1" rowspan="1">Objective:</td><td colspan="1" rowspan="1">Allows a Cashier to process the calculated refund amount for a cancelled booking via theappropriate method — payment gateway reversal, cash, or bank transfer.</td></tr><tr><td colspan="1" rowspan="1">Primary Actor:</td><td colspan="1" rowspan="1">Cashier</td></tr><tr><td colspan="1" rowspan="1">Secondary Actor:</td><td colspan="1" rowspan="1">Payment Gateway, Email Service</td></tr><tr><td colspan="1" rowspan="1">Trigger:</td><td colspan="1" rowspan="1">&lt;&lt;trigger&gt;&gt; from UC22 (Step 7) immediately after a booking is cancelled and a refund amount</td></tr><tr><td></td><td>has been calculated.</td></tr><tr><td>Pre-condition:</td><td>- UC22 has completed.</td></tr><tr><td></td><td>- A Refund record exists with the calculated amount and the originating booking's</td></tr><tr><td></td><td>source and payment method.</td></tr><tr><td>Post-condition:</td><td>- Refund disbursed (or recorded as a 0% refund).</td></tr><tr><td></td><td>- Customer notified via email (ET-06)</td></tr><tr><td>Main Flow:</td><td>Main Flow:</td></tr><tr><td></td><td>1. System creates a Refund record with the calculated refund amount and original</td></tr><tr><td></td><td>payment method. 2. Cashier reviews the refund details in the POS refund screen.</td></tr><tr><td></td><td>3. System processes refund based on original payment method and booking</td></tr><tr><td></td><td>source: If original payment = Cash (Offline): Cashier returns cash directly to the</td></tr><tr><td></td><td>customer at the counter. Cashier confirms the amount returned. If original payment = Card / POS Terminal: Cashier processes refund via</td></tr><tr><td></td><td>card terminal or bank transfer. o If original payment = Online (VNPay, MoMo, Visa): System initiates</td></tr><tr><td></td><td>gateway reversal (3–7 business days). If refund amount = 0%: System records zero-refund for audit only (no</td></tr><tr><td></td><td>O money movement). 4. Cashier confirms the refund has been completed.</td></tr><tr><td></td><td>5. System sends confirmation email to customer (ET-06) with refund details. 6. Use case ends successfully.</td></tr><tr><td>Alternative Flow:</td><td>AF1: Partial Refund (from partial seat cancellation) Refund amount is calculated only for cancelled seats; remaining seats stay CONFIRMED.</td></tr><tr><td>Exception Flow:</td><td>EF1: Payment Gateway reversal fails or times out (online refund) → System logs the failure and flags the refund for manual follow-up by the Cashier; Customer is notified</td></tr><tr><td></td><td>that processing may take additional time. EF2: Email delivery fails → System retries up to 3 times with exponential backoff; failure logged. Refund processing itself is not affected.</td></tr><tr><td></td><td>CBR-05</td></tr><tr><td>Business Rules:</td><td>BR-UC23-01: Refund Business Rule for Cashier</td></tr><tr><td></td><td>+ if Booking source = ONLINE, payment via VNPay/MoMo</td></tr><tr><td></td><td>+ Gateway reversal failed by system crash or other factors, bank transfer to original account</td></tr><tr><td></td><td>+ Booking source = OFFLINE, payment = cash =&gt; Cash refund at the counter</td></tr><tr><td></td><td></td></tr><tr><td></td><td>+ Booking source = OFFLINE, payment = card/QR =&gt; Bank transfer at the counter</td></tr></table>

## Loyalty Program

3.1.21 UC-24: View Loyalty Points & History
<table><tr><td colspan="1" rowspan="1">Objective:</td><td colspan="1" rowspan="1">Allows a Customer to view their current loyalty points balance and full transaction history,including earned, redeemed, reversed, and reinstated entries.</td></tr><tr><td colspan="1" rowspan="1">Primary Actor:</td><td colspan="1" rowspan="1">Customer</td></tr><tr><td colspan="1" rowspan="1">Secondary Actor:</td><td colspan="1" rowspan="1">None</td></tr><tr><td colspan="1" rowspan="1">Trigger:</td><td colspan="1" rowspan="1">Customer navigates to My Account → Đim thưng.</td></tr><tr><td colspan="1" rowspan="1">Pre-condition:</td><td colspan="1" rowspan="1">Customer is logged in.</td></tr><tr><td colspan="1" rowspan="1">Post-condition:</td><td colspan="1" rowspan="1">Customer views the current point balance and full transaction history.</td></tr><tr><td colspan="1" rowspan="1">Main Flow:</td><td colspan="1" rowspan="1">1. Customer goes to Profile and selects "Đim thưng".2. System displays current points balance prominently (e.g. 1,250 đim ≈ 125,000VNĐ) with expiry information.3. System shows transaction history table with columns: Ngày, Mô tå, Điêm (+/-).</td></tr><tr><td></td><td>4. Customer can filter history by date range or "Tt cå". 5. Use case ends successfully.</td></tr><tr><td>Alternative Flow:</td><td>None</td></tr><tr><td>Exception Flow:</td><td>EF1: No transaction history exists yet (new account) → System displays an empty state: "You haven't earned any points yet. Book a ticket to start earning!"</td></tr><tr><td>Business Rules:</td><td>CBR-07, CBR-13 BR-UC24-01: Points Expiry — Loyalty points not used (earned or redeemed) within 12 consecutive months automatically expire via a daily batch job. The system sends an</td></tr><tr><td colspan="2">3.1.22 UC-25: Redeem Loyalty Points</td></tr><tr><td>Objective:</td><td>Allows a Customer to apply accumulated loyalty points as a monetary discount against the ticket subtotal of an in-progress online booking.</td></tr><tr><td>Primary Actor:</td><td>Customer</td></tr><tr><td>Secondary Actor:</td><td>None</td></tr><tr><td>Trigger:</td><td>Invoked as &lt;&lt;extend&gt;&gt; from UC09 when Customer chooses to redeem points during checkout.</td></tr><tr><td>Pre-condition:</td><td>- Customer is in an active UC09 online booking session. - Customer's point balance ≥ minimum redemption threshold (BR-UC25-01)</td></tr><tr><td>Post-condition:</td><td>- Points deducted from balance - Ticket subtotal reduced by the redemption value; UC09 order total updated.</td></tr><tr><td>Main Flow:</td><td>1. During checkout (UC09), System displays the current point balance, its equivalent total monetary value (at the rate of 1 point = 100 VNĐ), and a slider bar to select the points to redeem. 2. Customer adjusts the slider to choose the number of points they want to use (System automatically sets the slider's minimum value to 50 and maximum value to the maximum allowed cap per BR-UC25-02) 3. System validates the selected points in real-time: amount $\le$ current balance; redemption value lesst than 50% of the ticket subtotal (BR-UC25-02). 4. System displays the corresponding discount amount ("Saving") and updates the UC09 order total in real time. 5. Customer clicks "Continue" to confirm the selection and proceed with the</td></tr><tr><td>Alternative Flow:</td><td>AF1: Customer cancels or adjusts the point selection before proceeding: 1. Customer drags the slider to a different value or back to 0.</td></tr><tr><td></td><td>2. System recalculates the discount and updates the total in real time. AF2: Customer clicks "Back":</td></tr><tr><td></td><td>1. System cancels the current point selection and returns to the previous step of UC09 without applying any discount.</td></tr><tr><td>Exception Flow:</td><td>EF1: Customer's total point balance is less than 50: System disables the point redemption section or displays a message: "Minimum 50 points required to redeem." (Redemption cannot be initiated).</td></tr><tr><td>Business Rules:</td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>CBR-07</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>BR-UC25-01: Minimum Redemption — A Customer must redeem at least 50 points per transaction.</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>BR-UC25-02: Maximum Redemption Cap — The monetary value of redeemed points in</td></tr><tr><td></td><td>a single booking must not exceed 50% of the ticket subtotal (after CBR-10 Step 4</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>discounts and any voucher applied), ensuring a non-zero payment remains.</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>BR-UC25-03: Offline Redemption Restriction — "Point redemption is only available via</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td>side fraud, since redemption reduces cash collected without a customer-initiated digital</td><td>the online, Customer-authenticated channel (UCo9). This restriction prevents counter-</td></tr></table>

## Movie & Schedule Management

3.1.23 UC-26: Manage Movie Information
<table><tr><td>Objective:</td><td>Allows the Cinema Manager to add new movies, edit movie information, update posters, manage publication status, and maintain the movie catalog.</td></tr><tr><td>Primary Actor:</td><td>Cinema Manager</td></tr><tr><td>Secondary Actor:</td><td>None</td></tr><tr><td>Trigger:</td><td>Cinema Manager navigates to Movies section.</td></tr><tr><td>Pre-condition:</td><td>Manager is logged in.</td></tr><tr><td>Post-condition:</td><td>Movie record created or updated; available for scheduling in UC28.</td></tr><tr><td>Main Flow:</td><td>Main Flow:</td></tr><tr><td></td><td>1. Manager clicks &quot;Movies&quot; in the left sidebar. 2. System displays the Movies Catalog screen as a grid of movie cards with filters:</td></tr><tr><td></td><td>All, Now Showing, Coming Soon, Archived. 3. Manager can:</td></tr><tr><td></td><td>Click &quot;+ Add movie&quot; to create a new movie, or</td></tr><tr><td></td><td>o</td></tr><tr><td></td><td>o Click &quot;Edit&quot; button on any movie card in the catalog.</td></tr><tr><td></td><td>4. System opens the Add / Edit Movie form.</td></tr><tr><td></td><td>5. Manager updates the following fields:</td></tr><tr><td></td><td>0</td></tr><tr><td>0</td><td>Poster (Drag &amp; drop or click to upload / Replace poster)</td></tr><tr><td>o</td><td>Title</td></tr><tr><td>o</td><td>Genre</td></tr><tr><td></td><td>Duration (minutes)</td></tr><tr><td>0</td><td>Rating (T13, T16, T18, .…)</td></tr><tr><td>o</td><td></td></tr><tr><td>o</td><td>Release Year</td></tr><tr><td>0</td><td>Director</td></tr><tr><td>0</td><td>Cast (comma-separated)</td></tr><tr><td></td><td>Synopsis</td></tr><tr><td></td><td> Trailer URL</td></tr><tr><td></td><td>6. Manager toggles the status between Draft and Published.</td></tr><tr><td></td><td>7. Manager clicks &quot;Save movie&quot; (or &quot;Save changes&quot;).</td></tr><tr><td></td><td>8. System validates the data and saves the movie record.</td></tr><tr><td></td><td>9. System returns to the Movies Catalog with updated information. 10. Use case ends successfully.</td></tr><tr><td>Alternative Flow:</td><td></td></tr><tr><td></td><td>AF1: Import from TMDB → Manager clicks Import button and proceeds to UC-27.</td></tr><tr><td>Exception Flow:</td><td>EF1: Required fields missing → System highlights and shows error. EF2: Invalid Trailer URL → “Please enter a valid YouTube or Vimeo URL.&quot;</td></tr><tr><td>Business Rules:</td><td>CBR-17 BR-UC26-01: Movies with existing bookings/reviews are never hard-deleted (soft hidden only).</td></tr></table>

## 3.1.24 UC-27: Import from TMDB

<table><tr><td colspan="1" rowspan="1">Objective:</td><td colspan="1" rowspan="1">Allows the Cinema Manager to search and import movie data from the TMDB external API,auto-populating movie fields to reduce manual data entry effort.</td></tr><tr><td colspan="1" rowspan="1">Primary Actor:</td><td colspan="1" rowspan="1">Cinema Manager</td></tr><tr><td colspan="1" rowspan="1">Secondary Actor:</td><td colspan="1" rowspan="1">Movie Content Provider (TMDB API)</td></tr><tr><td colspan="1" rowspan="1">Trigger:</td><td colspan="1" rowspan="1">Invoked as &lt;&lt;extend&gt;&gt; from UC26 (Step 3) when Manager clicks “Import from TMDB."</td></tr><tr><td colspan="1" rowspan="1">Pre-condition:</td><td colspan="1" rowspan="1">- TMDB API key is configured by System Admin (UC35).- Internet connectivity is available.</td></tr><tr><td colspan="1" rowspan="1">Post-condition:</td><td colspan="1" rowspan="1">Selected movie's metadata auto-populated into the UC26 form for Manager review.</td></tr><tr><td colspan="1" rowspan="1">Main Flow:</td><td colspan="1" rowspan="1">1. Manager clicks “Import from TMDB” within the Movie Management form.3. Manager enters a movie title to search.4. System sends the search query to the Movie Content Provider (TMDB API).5. TMDB returns a list of matching results: poster thumbnail, title, release year,and average rating.6. Manager selects the correct movie from the results.7. System auto-fills the UC26 form fields: Synopsis, Director, Lead Cast, Duration,Poster URL, Trailer URL, Genre.Manager reviews the imported data, makes any manual corrections, and proceeds</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">to save via UC26 Step 5.</td></tr><tr><td colspan="1" rowspan="1">Alternative Flow:</td><td colspan="1" rowspan="1">None</td></tr><tr><td colspan="1" rowspan="1">Exception Flow:</td><td colspan="1" rowspan="1">EF1: TMDB APl is unavailable or times out → “Unable to connect to TMDB. You cancontinue by entering movie details manually." Manager falls back to manual entry inUC26.EF2: No results match the search query  “No matching movies found on TMDB. Pleaserefine your search or enter details manually."</td></tr><tr><td colspan="1" rowspan="1">Business Rules:</td><td colspan="1" rowspan="1">None</td></tr><tr><td colspan="2" rowspan="1">3.1.25 UC-28: Manage Showtime Schedule</td></tr><tr><td colspan="1" rowspan="1">Objective:</td><td colspan="1" rowspan="1">Allows the Cinema Manager to create, edit, publish, and manage showtime schedules formovies across available screening rooms, subject to showtime freeze rules.</td></tr><tr><td colspan="1" rowspan="1">Primary Actor:</td><td colspan="1" rowspan="1">Cinema Manager</td></tr><tr><td colspan="1" rowspan="1">Secondary Actor:</td><td colspan="1" rowspan="1">None</td></tr><tr><td colspan="1" rowspan="1">Trigger:</td><td colspan="1" rowspan="1">Cinema Manager click Add Showtimes</td></tr><tr><td colspan="1" rowspan="1">Pre-condition:</td><td colspan="1" rowspan="1">At least one movie (status ≠ ENDED) and one screening room (status = ACTIVE) exist.</td></tr><tr><td colspan="1" rowspan="1">Post-condition:</td><td colspan="1" rowspan="1">- Showtime created, edited, or cancelled.- PUBLISHED showtimes become visible to Guest/Customer (UC06).</td></tr><tr><td colspan="1" rowspan="1">Main Flow:</td><td colspan="1" rowspan="1">1. Manager clicks "Showtimes" in the left sidebar.2. Manager clicks "+ New showtime" (or selects an existing showtime to edit).3. Manager selects: Movie, Room, Date, Start Time, and Format (e.g., 2DSubtitled).4. System automatically calculates End Time and displays Price Preview (Base price+ Room surcharge + Time multiplier).5. Manager reviews the computed price and sets the showtime status.6. Manager clicks "Publish showtime".7. System validates no time overlap and generates the seat map for the showtime.8. Use case ends successfully.</td></tr><tr><td colspan="1" rowspan="1">Alternative Flow:</td><td colspan="1" rowspan="1">AF1: Edit existing showtime: Manager edits date/time/room of a draft showtime (nobookings yet) → System re-validates overlap before saving. If there is any othershotimes overlap with that showtime, system warn Cinema Manager and suggest theychange fields and save settings</td></tr><tr><td colspan="1" rowspan="1">Exception Flow:</td><td colspan="1" rowspan="1">EF1: Time overlap with another showtime →“This showtime conflicts with an existingshowtime in this room."EF2: Room is under maintenance → “This room is currently under maintenance."EF3: Showtime has already started → Cannot modify.</td></tr><tr><td colspan="1" rowspan="1">Business Rules:</td><td colspan="1" rowspan="1">CBR-09, CBR-16, CBR-17BR-UC28-01: Showtime Overlap Validation — Two showtimes in the same screeningroom must not overlap. The end time of each showtime is defined as start time + movieduration + a 15-minute cleaning buffer; this full range must not intersect with any othershowtime in the same room.BR-UC28-02: Cancellation Restriction — A showtime with one or more CONFIRMEDbookings cannot be cancelled directly by the Cinema Manager through this use case;such cases require System Admin intervention to ensure affected bookings are properlyrefunded first.</td></tr></table>

3.1.26 UC-29: Manage Screening Rooms & Layouts
<table><tr><td colspan="1" rowspan="1">Objective:</td><td colspan="1" rowspan="1">Allows the Cinema Manager to configure screening rooms including seat layout, room type(2D/3D/IMAX/4DX), total capacity, and maintenance status.</td></tr><tr><td colspan="1" rowspan="1">Primary Actor:</td><td colspan="1" rowspan="1">Cinema Manager</td></tr><tr><td colspan="1" rowspan="1">Secondary Actor:</td><td colspan="1" rowspan="1">None</td></tr><tr><td colspan="1" rowspan="1">Trigger:</td><td colspan="1" rowspan="1">Cinema Manager clicks Add New Room</td></tr><tr><td colspan="1" rowspan="1">Pre-condition:</td><td colspan="1" rowspan="1">Manager is logged in.</td></tr><tr><td colspan="1" rowspan="1">Post-condition:</td><td colspan="1" rowspan="1">Room and seat layout configured; available for showtime scheduling (UC28) and pricing (UC30).</td></tr><tr><td colspan="1" rowspan="1">Main Flow:</td><td colspan="1" rowspan="1">1. Manager clicks "Rooms" in the left sidebar.2. Manager clicks "+ Add New Room" or selects an existing room.3. Manager enters: Room Name, Room Type (IMAX, 2D, etc.), Grid Size (Rows ×Columns).4. Manager designs the interactive seat grid: assigns seat types (Standard, VIP,Sweetbox, etc.) to each position.5. Manager marks special seats (Blocked, Entrance, Projector booth, etc.).6. Manager configures Capacity, Surcharge, Screen Orientation, and Status (Active/ Maintenance).7. Manager clicks "Save room".8. Use case ends successfully.</td></tr><tr><td colspan="1" rowspan="1">Alternative Flow:</td><td colspan="1" rowspan="1">AF1: Manager toggles an ACTIVE room status to MAINTENANCE:1. System checks for upcoming PUBLISHED showtimes in this room (CBR-16).2. System displays a warning popup: "Phòng này có [N] sut chiu sp din ra.Chuyn sang Maintenance s hy các phiên gi gh đang hot đng. Tip tc?"3. Manager confirms to proceed.4. System immediately terminates any currently active seat-lock sessions in thisroom and releases the held seats (CBR-16).5. Flow ends</td></tr><tr><td colspan="1" rowspan="1">Exception Flow:</td><td colspan="1" rowspan="1">EF1: Manager attempts to reduce seating capacity or change seat-type assignments fora room with an upcoming showtime that already has bookings → “This room hasexisting bookings for an upcoming showtime. Layout changes may affect seatassignments — please review before saving." Manager must explicitly confirm toproceed.EF2: A required field is left blank, e.g. Room Name or Room Type → “[Field] isrequired." Room not saved.</td></tr><tr><td colspan="1" rowspan="1">Business Rules:</td><td colspan="1" rowspan="1">CBR-02, CBR-16, CBR-17</td></tr></table>

## 3.1.27 UC-30: Configure Seat Types & Ticket Pricing

<table><tr><td colspan="1" rowspan="1">Objective:</td><td colspan="1" rowspan="1">Allows the Cinema Manager to configure base ticket prices, day-type multipliers, roomsurcharges, and service fees. The system will automatically combine these with Seat Typemultipliers (from UC-41) to calculate the final ticket price.</td></tr><tr><td colspan="1" rowspan="1">Primary Actor:</td><td colspan="1" rowspan="1">Cinema Manager</td></tr><tr><td colspan="1" rowspan="1">Secondary Actor:</td><td colspan="1" rowspan="1">None</td></tr><tr><td colspan="1" rowspan="1">Trigger:</td><td colspan="1" rowspan="1">Cinema Manager navigates to Pricing on the left bar</td></tr><tr><td colspan="1" rowspan="1">Pre-condition:</td><td colspan="1" rowspan="1">Manager is logged in.</td></tr><tr><td colspan="1" rowspan="1">Post-condition:</td><td colspan="1" rowspan="1">New pricing configuration is saved and applied to future bookings</td></tr><tr><td colspan="1" rowspan="1">Alternative Flow:</td><td colspan="1" rowspan="1">AF1: Manager clicks Discard → Changes are cancelled.</td></tr><tr><td rowspan="2">Exception Flow:</td><td>EF1: Manager enters a negative or zero base price  “Base price must be a positive number." Configuration not saved.</td></tr><tr><td>EF2: Changes saved while some showtimes are already published → System notifies: “Pricing changes will apply to new bookings only. Previously locked bookings retain their original price."</td></tr><tr><td>Business Rules:</td><td>CBR-10</td></tr></table>

## 3.1.28 UC-41: Manage Seat Types Catalog

<table><tr><td>Objective:</td><td>Allows the Cinema Manager to manage the seat type catalog used for room layouts and dynamic pricing.</td></tr><tr><td>Primary Actor:</td><td>Cinema Manager</td></tr><tr><td>Secondary Actor:</td><td>None</td></tr><tr><td>Trigger:</td><td>Cinema Manager navigates to Seat Types.</td></tr><tr><td>Pre-condition:</td><td>- Cinema Manager is logged into an active session with valid authorization privileges.</td></tr><tr><td>Post-condition:</td><td>- Seat types are updated (created/edited/activated/deactivated) and the changes are immediately reflected in room layouts (UC-29) and pricing calculations.</td></tr><tr><td>Main Flow:</td><td>1. Manager clicks &quot;Seat Types&quot; in the left sidebar. 2. System displays the Seat Type Catalog table with columns: Type Name, Multiplier, Span, Color, Status, Actions. 3. Manager clicks &quot;+ Add New Seat Type&quot;. 4. Manager fills in the form:</td></tr><tr><td></td><td>o Type Name (e.g., Sweetbox) Price Multiplier (e.g., 2.00) 0 Span (number of seats, e.g., 2) Color Code (color picker) 5. Manager sets initial Status (Active/Inactive) and saves. 6. To modify an existing seat type, Manager clicks &quot;Edit&quot; icon → updates fields and</td></tr><tr><td></td><td>saves. 7. Manager can toggle status by clicking &quot;Activate&quot; or &quot;Deactivate&quot; button in the Actions column. 8. System refreshes the table and shows success notification.</td></tr><tr><td>Alternative Flow:</td><td>9. Use case ends successfully.</td></tr><tr><td></td><td>AF1: Deactivate a seat type Manager clicks Deactivate on an ACTIVE seat type → System changes status to INACTIVE. The seat type remains in the catalog but is no longer assignable in new room layouts.</td></tr><tr><td></td><td>AF2: Activate a seat type Manager clicks Activate on an INACTIVE seat type → System changes status to ACTIVE.</td></tr><tr><td></td><td></td></tr><tr><td>Exception Flow:</td><td>EF1: Duplicate Type Name. Stop at step 6 (or AF1 step 4). System detects the Name</td></tr><tr><td></td><td>already exists in non-deleted records. Show: &quot;This Seat Type Name already exists. Please choose a unique name.&quot;</td></tr><tr><td></td><td>EF2: Invalid Price Multiplier. Stop at step 6. System detects value $&lt; 1.0$. Show: &quot;Price Multiplier must be equal to or greater than 1.0.&quot;</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>EF3: Attempt to deactivate a seat type currently in use in active room layouts or showtimes → System shows warning: “This seat type is currently in use. Deactivation may affect existing rooms. Continue anyway?&quot; (Manager must confirm)</td></tr><tr><td>Business Rules:</td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>BR-UC41-01: Name Uniqueness — The Type Name field must be unique among all non- deleted catalog records.</td></tr><tr><td></td><td>BR-UC41-02: Base Price Multiplier — The Price Multiplier must be a decimal value must be greater or equal 1.0 (e.g., Standard = 1.0, VIP = 1.2, Sweetbox = 1.5).</td></tr><tr><td></td><td></td></tr><tr><td></td><td>BR-UC41-03: Seat types are never hard-deleted; they can only be deactivated (soft deactivation via status).</td></tr></table>

## Promotions & Reviews

3.1.29 UC-31: Manage Promotions And Voucher Campaigns
<table><tr><td>Objective:</td><td>Allows the Cinema Manager to create, edit, publish, and manage promotion campaigns,</td></tr><tr><td></td><td>including both Tier 2 Automatic promotions and Tier 3 Voucher Code campaigns.</td></tr><tr><td>Primary Actor:</td><td>Cinema Manager</td></tr><tr><td>Secondary Actor:</td><td>Email Service</td></tr><tr><td>Trigger:</td><td>Cinema Manager navigates to the Vouchers section.</td></tr><tr><td>Pre-condition:</td><td>Manager is logged in.</td></tr><tr><td>Post-condition:</td><td>Campaign published; voucher codes (Tier 3) or an automatic promotion (Tier 2) become active in the system per CBR-11. 1. Manager clicks &quot;Vouchers&quot; in the left sidebar.</td></tr><tr><td>Main Flow:</td><td>2. System displays the Vouchers &amp; Promotions list screen showing: Active Campaigns KPI, Total Redemptions Today, Discount Given Today, and a table of all campaigns (Code, Description, Usage, Expires, Status). 3. Manager clicks &quot;+ New campaign&quot; button. 4. System opens the New Promotion Campaign form. 5. Manager selects campaign tier: Tier 2 — Automatic or Tier 3 — Voucher Code. 6. Manager fills in the following information:</td></tr><tr><td></td><td>o Discount Type (Percentage or Fixed Amount) and Discount Value o For Tier 3: Voucher Code, Valid From / Valid Until, Max Redemptions o Scope Restrictions (Specific movies, Time slots, Seat types, Min booking tier) 0 Description o Optional: Enable Batch Generate codes and Send announcement email to members.</td></tr><tr><td></td><td>7. System displays real-time Review panel on the right side summarizing the campaign. 8. Manager clicks &quot;Publish campaign&quot;. 9. System validates the campaign (see Exception Flows) and publishes it. 10. System returns to the list screen with updated status. 11. Use case ends successfully.</td></tr><tr><td>Alternative Flow:</td><td>EF1: Total discount exceeds the maximum allowed (CBR-11) → System shows warning and prevents publishing. EF2: Voucher code already exists →“This voucher code already exists. Please choose a different code.&quot; EF3: Valid Until date is earlier than Valid</td></tr><tr><td></td><td>From → “End date must be after the start date.&quot; EF4: Required fields are missing (Campaign Name, Discount Value, etc.) → System highlights the missing fields. EF5: Max Redemptions is set to 0 for Tier 3 → “Maximum redemptions must be greater than 0.&quot;</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td>Exception Flow:</td><td>EF1: The configured discount, combined with existing Tier 1/Tier 2 rules, would exceed</td></tr><tr><td></td><td>the 39% cap defined in CBR-11 → System displays a warning and prevents publishing</td></tr><tr><td></td><td>until the Manager adjusts the discount value.</td></tr><tr><td></td><td></td></tr><tr><td></td><td>EF2: Voucher code entered already exists in the system  “This voucher code already</td></tr><tr><td></td><td>exists. Please choose a different code.&quot;</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>EF3: Validity period end date is earlier than the start date → “End date must be after</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>the start date.&quot; Campaign not saved.</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td>Business Rules:</td><td></td></tr></table>

3.1.30 UC-32: Submit Movie Review & Rating
<table><tr><td rowspan=1 colspan=1>Objective:</td><td rowspan=1 colspan=1>Allows a Customer who has attended a showtime (CHECKED_IN status) to submit a star ratingand written review for the movie, pending moderation before public display.</td></tr><tr><td rowspan=1 colspan=1>Primary Actor:</td><td rowspan=1 colspan=1>Customer</td></tr><tr><td rowspan=1 colspan=1>Secondary Actor:</td><td rowspan=1 colspan=1>None</td></tr><tr><td rowspan=1 colspan=1>Trigger:</td><td rowspan=1 colspan=1>Customer navigates to a CHECKED_IN booking in their history and clicks “Write a Review,&quot; orclicks a review-prompt notification sent after the showtime ends.</td></tr><tr><td rowspan=1 colspan=1>Pre-condition:</td><td rowspan=1 colspan=1>- Customer has a booking with status = CHECKED_IN for the movie being reviewed.- Customer has not already submitted a review for this specific showtime (BR-UC32-01).</td></tr><tr><td rowspan=1 colspan=1>Post-condition:</td><td rowspan=1 colspan=1>Review saved with status = PENDING, awaiting Cinema Manager moderation (UC33).</td></tr></table>

<table><tr><td>Main Flow:</td><td>review text. 4. Customer submits → System validates that no prior review exists for this</td><td>1. Customer navigates to My Account → Booking History → selects a CHECKED_IN booking → clicks “Write a Review.&quot; 2. System displays the review form: star rating (1–5) and an optional written 3. Customer selects a star rating and optionally writes review text.</td></tr><tr><td>Alternative Flow:</td><td>AF1: Customer submits a star rating only, without written text: required.</td><td>(UC07) only after approval in UC33. 1. System accepts the review since written text is optional; only the star rating is</td></tr><tr><td rowspan="2">Exception Flow:</td><td>EF1: Customer attempts to review a movie they have not attended, i.e. no CHECKED_IN booking for that showtime →“You can only review movies you&#x27;ve watched.&quot; Review</td><td rowspan="2"></td></tr><tr><td>form not accessible. EF2: Customer attempts to submit a second review for a showtime they already reviewed (BR-UC32-01) →“You have already reviewed this showtime.&quot; Submission blocked.</td></tr><tr><td>Business Rules:</td><td>CBR-17</td><td>BR-UC32-01: One Review Per Showtime — A Customer may submit at most one review per CHECKED_IN showtime attended. A second submission for the same showtime is rejected. BR-UC32-01: Review Submission Window: A customer may submit a review for a movie within</td></tr></table>

## 3.1.31 UC-33: Moderate Movie Reviews

<table><tr><td rowspan=1 colspan=1>Objective:</td><td rowspan=1 colspan=1>Allows the Cinema Manager to review, approve, or reject customer-submitted movie reviewsbefore they are published on the public movie detail page.</td></tr><tr><td rowspan=1 colspan=1>Primary Actor:</td><td rowspan=1 colspan=1>Cinema Manager</td></tr><tr><td rowspan=1 colspan=1>Secondary Actor:</td><td rowspan=1 colspan=1>None</td></tr><tr><td rowspan=1 colspan=1>Trigger:</td><td rowspan=1 colspan=1>Cinema Manager navigates to Review Management.</td></tr><tr><td rowspan=1 colspan=1>Pre-condition:</td><td rowspan=1 colspan=1>At least one review with status = PENDING exists.</td></tr><tr><td rowspan=1 colspan=1>Post-condition:</td><td rowspan=1 colspan=1>- Review status = APPROVED (visible on UC07) or REJECTED (hidden, with a logged reason).- Movie&#x27;s average rating recalculated if approved.</td></tr><tr><td rowspan=1 colspan=1>Main Flow:</td><td rowspan=1 colspan=1>1. Manager navigates to Review Management → views the list of PENDINGreviews.2. Manager opens a review: movie title, Customer name, star rating, written text,submission date.3. Manager decides: Approve → review status = APPROVED, becomes visible onthe movie&#x27;s detail page (UC07); or Reject → review status = REJECTED, Managerenters a reason (not shown publicly).4. If approved, system recalculates the movie&#x27;s average star rating across allAPPROVED reviews.5. Use case ends successfully.</td></tr><tr><td rowspan=1 colspan=1>Alternative Flow:</td><td rowspan=1 colspan=1>AF1: Manager filters the PENDING queue by movie or by submission date:1. System updates the displayed list accordingly to help prioritize moderation.2. Flow continues at step 2</td></tr><tr><td rowspan=1 colspan=1>Exception Flow:</td><td rowspan=1 colspan=1>EF1: Manager attempts to reject a review without entering a reason → System requiresa reason before the rejection can be confirmed, for internal audit purposes.</td></tr><tr><td rowspan=1 colspan=1>Business Rules:</td><td rowspan=1 colspan=1>None</td></tr></table>

## Administrative

## 3.1.32 UC-34: Manage User Accounts & Roles

<table><tr><td>Objective:</td><td>Allows the System Admin to create, view, edit, activate, deactivate, lock/unlock accounts, and assign roles and cinema locations for all users in the system.</td></tr><tr><td>Primary Actor:</td><td>System Admin</td></tr><tr><td>Secondary Actor:</td><td>Email Service</td></tr><tr><td>Trigger:</td><td>System Admin navigates to Accounts in the Admin Panel.</td></tr><tr><td>Pre-condition:</td><td>- System Admin is logged in.</td></tr><tr><td></td><td>- System Admin has SYSTEM_ADMIN role.</td></tr><tr><td>Post-condition:</td><td>• New staff account created and active (if creation flow).</td></tr><tr><td></td><td>• Account status updated (ACTIVE / INACTIVE / LOCKED) as requested.</td></tr><tr><td></td><td>• Role assignment saved and effective on next login for the affected Actor.</td></tr><tr><td></td><td>• Where applicable, Email Service notified to deliver credentials or status notice.</td></tr><tr><td></td><td>• Changes are logged to Audit Log.</td></tr><tr><td>Main Flow:</td><td>Main Flow:</td></tr><tr><td></td><td>1. System Admin clicks &quot;Accounts&quot; in the left sidebar. 2. System displays the user table with columns: User, Email, Role, Cinema (Assigned), Status, Last Login, Actions. 3. System Admin can search by name/email/phone and filter by Role or Status. 4. System Admin performs actions: Click &quot;+ Create account&quot; to open creation form.</td></tr><tr><td></td><td>o Click &quot;Edit&quot; on any row to update information. Click &quot;Lock&quot; / &quot;Unlock&quot; directly from the table. 5. System Admin can select multiple users and use Bulk Activate / Bulk Deactivate. 6. All changes are saved and automatically logged to Audit Log. 7. Use case ends successfully.</td></tr><tr><td></td><td></td></tr><tr><td>Alternative Flow:</td><td>AF1: Create New Account</td></tr><tr><td></td><td>1. Admin fills: Full Name, Username, Email, Phone, Temporary Password, Role, Assigned Cinemas, Status.</td></tr><tr><td></td><td>2. System creates account and sends credentials via Email Service.</td></tr><tr><td></td><td>AF2: Edit Account Admin updates role, assigned cinemas, or status. Changes take effect on next login.</td></tr><tr><td></td><td>AF3: Deactivate or Reactivate Account:</td></tr><tr><td></td><td>1. System Admin selects a user →clicks &quot;Deactivate&quot; or &quot;Activate&quot;. 2. System updates account status accordingly.If deactivated: all active sessions for that account are invalidated immediately. Flow ends.</td></tr><tr><td></td><td>AF4: Unlock Locked Account:</td></tr><tr><td></td><td>1. System Admin selects a locked account → clicks &quot;Unlock&quot;.</td></tr><tr><td>Exception Flow:</td><td>2. System resets the failed login counter to 0 and sets status = ACTIVE. Flow ends. EF1: Email already in use. At AF1 step 2  System displays: &quot;Email has been used&quot;</td></tr><tr><td></td><td>System Admin must provide a unique email. EF2: System Admin attempts to deactivate their own account → Action blocked. System</td></tr><tr><td>Business Rules:</td><td>displays: &quot;You cannot deactivate your own account.&quot;</td></tr><tr><td></td><td>CBR-17 BR-UC34-01: Role Hierarchy — System Admin cannot assign a role higher than their own. A</td></tr><tr><td></td><td>System Admin account cannot be created by a non-System Admin.</td></tr><tr><td></td><td></td></tr><tr><td></td><td>BR-UC34-02: Cinema Scope — When creating or editing a Cinema Manager or Cashier account,</td></tr><tr><td></td><td></td></tr><tr><td></td><td>at least one cinema location must be assigned. Operations performed by that actor are scoped</td></tr><tr><td></td><td>to assigned locations only (per CBR multi-location rule).</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>BR-UC34-03: Audit Trail — All account creation, role changes, deactivation, and unlock actions</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>are logged with actor ID, timestamp, and target account ID,</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr></table>

## 3.1.33 UC-35: Configure System Settings

<table><tr><td>Objective:</td><td colspan="2">Allows the System Admin to view, filter, and export the immutable system-wide audit log, which records all sensitive actions performed by any Actor across all use cases.</td></tr><tr><td>Primary Actor:</td><td colspan="2">System Admin</td></tr><tr><td>Secondary Actor:</td><td colspan="2">None</td></tr><tr><td>Trigger:</td><td colspan="2">System Admin navigates to Admin Panel → System Settings.</td></tr><tr><td>Pre-condition:</td><td colspan="2">- System Admin is logged in.</td></tr><tr><td></td><td colspan="2">- System Admin has SYSTEM_ADMIN role</td></tr><tr><td>Post-condition:</td><td>• Updated settings are persisted and applied system-wide.</td><td></td></tr><tr><td></td><td></td><td>• Relevant business rules referencing these settings use the updated values on their next</td></tr><tr><td></td><td>execution. • All setting changes are written to the audit log.</td><td></td></tr><tr><td>Main Flow:</td><td></td><td>1. System Admin clicks &quot;System Settings&quot; in the left sidebar. 2. System displays grouped sections:</td></tr><tr><td></td><td>o o 3. Admin edits the desired fields. 4. Admin clicks &quot;Save all settings&quot;. 5. System validates inputs and persists changes. 6. All modifications are logged to Audit Log. 7. Use case ends successfully.</td><td>o Manage Calendar &amp; Holidays (calendar view, add/edit holiday). Operational Settings (Service Fee, Seat Lock Timeout, Payment Timeout, OTP settings, Account Lockout, etc.). API Keys (TMDB, SendGrid, Twilio, VNPay... with Rotate button).</td></tr><tr><td>Alternative Flow:</td><td>AF1: Manage Holidays Admin adds new holiday or edits existing one via calendar interface.</td><td></td></tr><tr><td>Exception Flow:</td><td>holiday entry for this date already exists.&quot;</td><td>EF1: System Admin enters a conflicting holiday date (duplicate). At step 5 → &quot;A public</td></tr><tr><td>Business Rules:</td><td>CBR-17 BR-UC35-01: Setting Audit — Every change to system configuration is logged and visible to</td><td></td></tr></table>

## 3.1.34 UC-36: View Audit Log

<table><tr><td colspan="1" rowspan="1">Objective:</td><td colspan="1" rowspan="1">Allows the System Admin to view, filter, and export the immutable system-wide audit log, whichrecords all sensitive actions performed by any Actor across all use cases.</td></tr><tr><td colspan="1" rowspan="1">Primary Actor:</td><td colspan="1" rowspan="1">System Admin</td></tr><tr><td colspan="1" rowspan="1">Secondary Actor:</td><td colspan="1" rowspan="1">None</td></tr><tr><td colspan="1" rowspan="1">Trigger:</td><td colspan="1" rowspan="1">System Admin navigates to Admin Panel → Audit Log.</td></tr><tr><td colspan="1" rowspan="1">Pre-condition:</td><td colspan="1" rowspan="1">- System Admin is logged in.- System Admin has SYSTEM_ADMIN role.</td></tr><tr><td colspan="1" rowspan="1">Post-condition:</td><td colspan="1" rowspan="1">• System Admin has viewed and/or exported the requested audit log entries.• No audit log record is created, modified, or deleted by this use case.• Viewing the audit log itself does not generate a new audit log entry.</td></tr><tr><td colspan="1" rowspan="1">Main Flow:</td><td colspan="1" rowspan="1">1. System Admin clicks "Audit Log" in the left sidebar.2. System displays the audit log table in reverse-chronological order with columns:Timestamp, User, Role, Action (color-coded), Entity, Detail, IP Address.3. Admin applies filters: All Users, All Actions, Date Range.4. System refreshes the table based on filters.5. Admin can click "Export CSV" to download the filtered log.6. Use case ends successfully.</td></tr><tr><td colspan="1" rowspan="1">Alternative Flow:</td><td colspan="1" rowspan="1">AF1: Export Audit Log (CSV):1. At step 4, System Admin clicks "Export CSV".2. System generates a CSV file containing all records matching the current filters.CSV columns: Timestamp, Username, Role, Action, Entity, Detail, IP Address.3. File downloads automatically. File name format: audit_log_YYYYMMDD_YYYYMMDD.csv.4. Return to Step 4 of Main Flow. Flow ends.</td></tr><tr><td colspan="1" rowspan="1">Exception Flow:</td><td colspan="1" rowspan="1">EF1: No records match the selected filters → System displays: "No audit log entries</td></tr><tr><td></td><td>found for the selected filters. Please adjust your criteria."</td></tr><tr><td>Business Rules:</td><td>EF2: Export fails (e.g., very large date range causing server timeout) → System displays: "Export failed. Please narrow the date range and try again." BR-UC39-01: Immutability — Audit log records are read-only and immutable. No Actor —</td></tr><tr><td></td><td>including System Admin — can edit, delete, or suppress any audit log entry. This is enforced at the database level.</td></tr><tr><td></td><td>BR-UC39-02: Retention Policy — Audit log entries are retained for a minimum of 365 days from</td></tr><tr><td></td><td>the date of creation. Records beyond 365 days may be archived to cold storage but remain accessible via export on request.</td></tr><tr><td></td><td></td></tr><tr><td></td><td>BR-UC39-03: Access Restriction — The Audit Log screen is accessible exclusively to System</td></tr><tr><td></td><td>Admin. Cinema Manager, Cashier, Concession Staff, and Customer roles have no access.</td></tr><tr><td></td><td>BR-UC39-04: What Is Logged — The following events must generate an audit log entry:</td></tr><tr><td></td><td></td></tr><tr><td></td><td>- Account creation, role change, deactivation, unlock (UC-34)</td></tr><tr><td></td><td>- System settings changes (UC-35) — records old value and new value</td></tr><tr><td></td><td>- All payment transactions and refunds (UC-13, UC-23)</td></tr><tr><td></td><td>- Booking cancellations — full and partial (UC-22)</td></tr><tr><td></td><td>- Movie record creation, edit, publish, delete (UC-26)</td></tr><tr><td></td><td>- Showtime creation, edit, cancel (UC-28)</td></tr><tr><td></td><td>- Pricing configuration changes (UC-30)</td></tr><tr><td></td><td></td></tr><tr><td></td><td>- Voucher/campaign creation and deletion (UC-31)</td></tr><tr><td></td><td>- Review approvals and rejections (UC-33)</td></tr><tr><td></td><td>- All login, logout, and failed login events (UC-02, UC-03) BR-UC39-05: Audit Entry Fields — Every log entry must capture: timestamp (UTC), actor user ID,</td></tr><tr><td>IP address.</td><td>actor role, action type, affected entity type and ID, change detail (human-readable), and client</td></tr><tr><td></td><td>BR-UC39-06: Self-Exclusion — Viewing the Audit Log (this UC) does not itself generate an audit</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>log entry, to prevent infinite self-referential logging.</td></tr></table>

3.1.35 UC-37: View Report And Dashboard
<table><tr><td rowspan=1 colspan=1>Objective:</td><td rowspan=1 colspan=1>Allows the Cinema Manager and System Admin to view a real-time operational dashboard forthe current day (Dashboard) and to generate historical reports with configurable date range(Reports), view comprehensive system-wide reports covering user growth, login activity,account statistics, and top audited actions over selectable time periods.</td></tr><tr><td rowspan=1 colspan=1>Primary Actor:</td><td rowspan=1 colspan=1>Cinema Manager, System Admin</td></tr><tr><td rowspan=1 colspan=1>Secondary Actor:</td><td rowspan=1 colspan=1>None</td></tr><tr><td rowspan=1 colspan=1>Trigger:</td><td rowspan=1 colspan=1>Actor navigates to Dashboard from the left sidebar or navigates to Reports from the leftsidebar.</td></tr><tr><td rowspan=1 colspan=1>Pre-condition:</td><td rowspan=1 colspan=1>• Actor is logged in with Cinema Manager or System Admin role.• Cinema Manager: scoped to their assigned cinema location(s) only.• System Admin: access to all locations; can filter by location.</td></tr><tr><td rowspan=1 colspan=1>Post-condition:</td><td rowspan=1 colspan=1>• Actor has viewed the requested data. No data is created, modified, or deleted.• Exported file downloaded if AF1 or AF2 was triggered.</td></tr><tr><td rowspan=1 colspan=1>A. Main Flow(Dashboard)</td><td rowspan=1 colspan=1>1. Actor clicks &quot;Dashboard&quot; in the left sidebar.2. System displays the System Overview Dashboard with header &quot;Real-time systemhealth &amp; user activity&quot;.3. System renders four KPI cards:oActive Users (24h)0Total Accountso System Uptime (e.g. 99.98%)oFailed Logins (24h)4. System displays two main charts side-by-side:oLogins per hour (24h) – bar chart (Live). Accounts by role – pie chart (Customer, Cashier, Manager, Admin).5. System displays Recent activity panel showing latest actions (timestamp, user,action description, status).6. Dashboard auto-refreshes every 30–60 seconds.7. Use case ends successfully.</td></tr><tr><td rowspan=1 colspan=1>B. Main Flow (Report)</td><td rowspan=1 colspan=1>1. Actor clicks &quot;Reports&quot; in the left sidebar.</td></tr></table>

<table><tr><td rowspan="7"></td><td></td><td>2. System displays the Reports page with a time-period selector at the top right (default: Last 6</td></tr><tr><td>months).</td><td>3. System renders four KPI cards for the selected period:</td></tr><tr><td></td><td>New Accounts (6MO)</td></tr><tr><td></td><td> Total Logins</td></tr><tr><td> Avg Session</td><td></td></tr><tr><td> Incident Count</td><td></td></tr><tr><td></td><td>4. System displays User Growth (6 months) line/area chart showing monthly account growth.</td></tr><tr><td rowspan="6"></td><td></td></tr><tr><td>5. System displays Login Activity by Role table with columns: Role, Active Accounts, Logins (30d), Avg Session, Failed Logins.</td></tr><tr><td>6. System displays Top Audited Actions (30d) horizontal bar chart showing the most frequent</td></tr><tr><td>actions (e.g., Account created, Showtime edited, Refund approved, etc.).</td></tr><tr><td>7. System Admin can change the time period to refresh all data.</td></tr><tr><td>8. System Admin can click Export PDF or Export CSV.</td></tr><tr><td rowspan="6">Alternative Flow:</td><td></td><td>9. Use case ends successfully.</td></tr><tr><td>AF1: Quick actions (Dashboard)</td><td></td></tr><tr><td>• Click &quot;View audit log&quot;  navigates to UC-36.</td><td>• Click &quot;+ New account&quot;  navigates to UC-34 (Create Account).</td></tr><tr><td></td><td></td></tr><tr><td>AF2 (Reports): Export Report Admin clicks Export PDF or Export CSV → System</td><td></td></tr><tr><td>Exception Flow:</td><td>generates and downloads the file for the selected period.</td></tr><tr><td></td><td></td><td>EF1 (Dashboard): No data available → Empty state or &quot;0&quot; is displayed on cards/charts. EF2 (Reports): No data for selected period → Empty state displayed on charts/tables.</td></tr><tr><td>Business Rules:</td><td>BR-UC37-02: Reports and Dashboard are read-only.</td><td>BR-UC37-01: System Admin has full access to all locations and global metrics.</td></tr></table>

## Others

3.12.1 UC-38: Chat with AI Support
<table><tr><td>Objective:</td><td>Allows a logged-in Customer to interact with an Al-powered chatbot to receive personalised movie recommendations, showtime suggestions, and automated answers to booking-related or cinema policy questions.</td></tr><tr><td>Primary Actor:</td><td>Customer</td></tr><tr><td>Secondary Actor:</td><td>Al Support</td></tr><tr><td>Trigger:</td><td>Customer clicks the Al Support chat icon available on any page while logged in.</td></tr><tr><td>Pre-condition:</td><td>• Customer is logged in. • Al Support service is available and reachable.</td></tr><tr><td>Post-condition:</td><td>• Customer has received a response from the Al Support service. • No booking or account data has been modified by this use case.</td></tr><tr><td>Main Flow</td><td>1. Customer clicks the Al Support chat icon.</td></tr><tr><td></td><td>2. System opens the chat widget and displays a greeting message and suggested quick-action prompts</td></tr><tr><td></td><td>(e.g., "Recommend a movie for tonight", "What is the cancellation policy?").</td></tr><tr><td></td><td>3. Customer types a message or selects a quick-action prompt.</td></tr><tr><td></td><td>4. System sends to Al Support service: Customer's message, customer profile context (booking history,</td></tr><tr><td></td><td>preferred genres), current movie catalogue (titles, genres, showtimes, ratings), active session context.</td></tr><tr><td></td><td></td></tr><tr><td></td><td>5. Al Support returns a response.</td></tr><tr><td></td><td>6. System displays the response in the chat widget.</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">7. Customer may continue the conversation (repeat steps 3-6) or close the widget.8. Use case ends.</td></tr><tr><td colspan="1" rowspan="1">Alternative Flow:</td><td colspan="1" rowspan="1">AF1: Customer asks to book a movie the Al recommends:At step 6, Al response includes a direct link to the movie's showtime (UC-07 or UC-09).1. Customer clicks the link and is navigated to the booking flow.2. Chat widget closes or minimises. Flow ends.</td></tr><tr><td colspan="1" rowspan="1">Exception Flow:</td><td colspan="1" rowspan="1">EF1: Al Support service unavailable. At step 5 → chat widget displays: "Al Support istemporarily unavailable. Please contact our staff or browse our FAQ for assistance."EF2: Customer sends an empty or very short message (&lt; 2 characters). At step 4 →System displays: "Please enter a message to continue." Flow repeats from step 3.</td></tr><tr><td colspan="1" rowspan="1">Business Rules:</td><td colspan="1" rowspan="1">BR-UC37-01: Read-Only Al Access — The Al Support service has read access to the moviecatalogue, showtime data, and the current Customer's profile context only. It cannot modifyany booking, account, or system data.BR-UC37-02: Data Privacy — Customer's full name, phone number, and payment details are notpassed to the Al Support service. Only anonymised behavioural context (genre preferences,booking history by category) is shared.BR-UC37-03: Scope Limitation — Al Support is accessible to logged-in Customers only. Guestusers see only a static FAQ link, not the interactive chatbot.</td></tr></table>

3.12.2 UC-39: Automated Showtime Reminder (System-initiated)
<table><tr><td colspan="2">Objective:</td><td>Automatically sends an SMS showtime reminder to Customers with a CONFIRMED booking, executed by a scheduled system job that runs periodically and delivers the reminder</td></tr><tr><td colspan="2"></td><td>approximately 1 hour before the showtime starts.</td></tr><tr><td colspan="2">Primary Actor:</td><td>System (automated scheduled job — no human initiator)</td></tr><tr><td colspan="2"></td><td></td></tr><tr><td colspan="2">Secondary Actor:</td><td>SMS Service</td></tr><tr><td colspan="2">Trigger:</td><td>Scheduled job fires at a configured interval (e.g., every 5 minutes). Execution context: current time T. Job processes all eligible bookings.</td></tr><tr><td colspan="2">Pre-condition:</td><td>• Booking status = CONFIRMED.</td></tr><tr><td colspan="2"></td><td>• Booking is linked to a Customer account with a registered phone number.</td></tr><tr><td colspan="2"></td><td>showtime_start – T ≤ 60 minutes AND showtime_start – T &gt; 0 (showtime has not yet</td></tr><tr><td colspan="2"></td><td>started).</td></tr><tr><td colspan="2"></td><td>• reminder_sent flag = false for this booking.</td></tr><tr><td colspan="2"></td><td>• SMS Service is reachable.</td></tr><tr><td colspan="2">Post-condition:</td><td>• SMS reminder delivered to the Customer's registered phone number.</td></tr><tr><td colspan="2"></td><td>• Booking record updated: reminder_sent = true, reminder_sent_at = timestamp.</td></tr><tr><td colspan="2"></td><td>Each eligible booking is processed exactly once.</td></tr><tr><td colspan="2"></td><td>• No booking or account data has been modified by this use case.</td></tr><tr><td colspan="2">Main Flow</td><td>1. Scheduled job fires.</td></tr><tr><td colspan="2"></td><td>2. System queries for all bookings where:</td></tr><tr><td colspan="2"></td><td></td></tr><tr><td colspan="2"></td><td>- status = CONFIRMED</td></tr><tr><td colspan="2"></td><td>- reminder_sent = false - 0 &lt; (showtime_start – now()) ≤ 60 minutes</td></tr><tr><td colspan="2"></td><td>- Customer account has a valid registered phone number.</td></tr><tr><td colspan="2"></td><td>3. For each eligible booking, System calls SMS Service with:</td></tr><tr><td colspan="2"></td><td>- Recipient phone number</td></tr><tr><td colspan="2"></td><td>- Message body: movie name, showtime date/time, cinema location, booking code.</td></tr><tr><td colspan="2"></td><td>4. SMS Service delivers the message.</td></tr><tr><td colspan="2"></td><td>5. System updates booking: reminder_sent = true, reminder_sent_at = now().</td></tr><tr><td colspan="2"></td><td>6. Job completes. Eligible bookings processed in this run = 0 or more.</td></tr><tr><td colspan="2">Alternative Flow:</td><td>None</td></tr><tr><td colspan="2"></td><td></td></tr><tr><td colspan="2">Exception Flow:</td><td>EF1: SMS delivery fails for a specific booking → failure logged with booking ID, phone (masked), and error</td></tr><tr><td colspan="2"></td><td>code. reminder_sent remains false. System will retry on the next job cycle if the booking is still within the</td></tr><tr><td colspan="2"></td><td>60-minute window and has not yet started.</td></tr><tr><td colspan="2"></td><td>EF2: Showtime has already started when the job processes a booking (race condition) → booking skipped</td></tr><tr><td colspan="2"></td><td>silently; reminder not sent; reminder_sent remains false. No retry</td></tr><tr><td colspan="2" rowspan="1"></td><td colspan="1" rowspan="1">EF3: SMS Service is unreachable → entire job cycle logs a service-unavailable error. All ligible bookingsremain unprocessed (reminder_sent = false). Job retries on next cycle.EF4: Customer phone number is null or invalid → booking skipped; failure logged. Noretry.</td></tr><tr><td colspan="2" rowspan="1">Business Rules:</td><td colspan="1" rowspan="1">BR-UC38-01: Exactly-Once Guarantee — The reminder_sent flag ensures each booking receivesat most one SMS reminder regardless of how many job cycles execute during the window.BR-UC38-02: No Customer Action Required — This use case is fully system-initiated. NoCustomer interaction triggers or controls this flow.BR-UC38-03: Relationship with UC-14 — UC-14 Step 4 schedules the intent for a reminder (setsthe expectation). UC-38 is the execution that fulfils that intent at the correct time.BR-UC38-04: Job Frequency — Configured by System Admin in UC-35 System Settings. Default:every 5 minutes.</td></tr><tr><td colspan="3" rowspan="1">3.12.3 UC-40: Identity Verification</td></tr><tr><td colspan="2" rowspan="1">Objective:</td><td colspan="1" rowspan="1">Allows a logged-in Customer to verify their identity by submitting CCCD/CMND front photo andselfie for validation through external service.</td></tr><tr><td colspan="2" rowspan="1">Primary Actor:</td><td colspan="1" rowspan="1">Customer</td></tr><tr><td colspan="2" rowspan="1">Secondary Actor:</td><td colspan="1" rowspan="1">External Identity Verification Service</td></tr><tr><td colspan="2" rowspan="1">Trigger:</td><td colspan="1" rowspan="1">Customer clicks "Xác thc CCCD" on Profile page.</td></tr><tr><td colspan="2" rowspan="1">Pre-condition:</td><td colspan="1" rowspan="1">- Customer is logged in.- Identity verification status is UNVERIFIED or REJECTED.</td></tr><tr><td colspan="2" rowspan="1">Post-condition:</td><td colspan="1" rowspan="1">- Identity verification status is updated to VERIFIED.- Verified Date of Birth is recorded in profile.</td></tr><tr><td colspan="2" rowspan="1">Main Flow</td><td colspan="1" rowspan="1">1. Customer goes to Profile page and clicks "Xác thc CCCD".2. System displays verification wizard with 4 steps.3. Customer completes each step: upload CCCD front photo, take selfie, face matching, andcompletion.4. System sends data to External Identity Verification Service.5. Service returns success result with extracted information.6. System updates profile (status = VERIFIED, verifiedDob).7. System displays success message “Xác thc thành công”.8. Use case ends successfully</td></tr><tr><td colspan="2" rowspan="1">Alternative Flow:</td><td colspan="1" rowspan="1">None</td></tr><tr><td colspan="2" rowspan="1">Exception Flow:</td><td colspan="1" rowspan="1">EF1: Invalid File Format or Size. Stop at step 5. System displays an error message: "Đnh dng tp khônghp I hoc dung lưng tp vưt quá 5MB. Vui lòng ti lên nh JPG/PNG dưi 5MB." (BR-UC40-01).EF2: Document Validation Failed (e.g., Fake ID, Blur image). Stop at step 8. External elDV returns an error.System sets status to REJECTED, logs the error reason, and displays: "Xác thc tht bi: Không th nhndin đưc tài liu. Vui lòng ti lên mt bc nh rõ nét."EF3: Facial Matching Failed (Selfie does not match ID photo). Stop at step 8. External elDV returns amismatch error. System sets status to REJECTED and displays: "Xác thc tht bi: Ành selfie không khpvi tài liu ca bn."EF4: External Service Timeout/Unavailable. Stop at step 7 or 8. System displays: "Dch v xác thc tmthi không khå dng. Vui lòng th li sau." No profile changes are saved.</td></tr><tr><td colspan="2" rowspan="1">Business Rules:</td><td colspan="1" rowspan="1">BR-UC40-01: Image Upload Restrictions — Allowed formats: ·jpg, -jpeg, .png. Maximum filesize: 5MB per image.BR-UC40-02: Age Restriction Check — The extracted verifiedDob will be used to enforce age-restricted movie ratings during checkout.</td></tr><tr><td colspan="3" rowspan="1">Common Business RuleThis section defines business rules that are used across use cases and can be considered as common rules. Each commonbusiness rule below is applied only for use cases that have reference to it.</td></tr><tr><td colspan="1" rowspan="1">BR Code</td><td colspan="2" rowspan="1">Description</td></tr><tr><td colspan="1" rowspan="1">CBR-01</td><td colspan="2" rowspan="1">Seat Locking: When a Customer or Cashier selects a seat, the system immediately locks it for 10 minutesstarting from the moment the first seat in the session is selected. The timer is shared across all seats inthe same session and does not reset when additional seats are added. If payment is not completed withinthis window, all locked seats are simultaneously released back to Available status. The Ul displays a real-time countdown; a red warning appears when 1 minute remains. Once the user proceeds to the paymentgateway, a separate 15-minute payment phase begins (CBR-06) and the seat lock is no longer subject toexpiry under this rule. Applies to: UC10, UC16.</td></tr><tr><td colspan="1" rowspan="1">CBR-02</td><td colspan="2" rowspan="1">No Orphan Seat: The system must prevent any seat selection that would result in a single empty seatisolated between two occupied or locked seats within the same row. Validation occurs in real-time uponeach seat click, before the seat (or seat-pair) is locked. A selection is blocked if it would leave exactly oneempty seat sandwiched on both sides by booked or locked seats.Paired-seat handling (e.g. Sweetbox, seatsPerUnit &gt; 1): A seat pair is treated as a single indivisible unit forthe purpose of this rule. The two physical seats within a pair are never sold, locked, or evaluatedseparately — the gap between the two seats inside a pair is never checked for orphan status, since bothseats always transact together. Orphan-check is instead applied at the unit boundary: the systemevaluates whether selecting the pair would leave exactly one empty single-seat unit immediately outsideeither edge of the pair.Exceptions:1. If 3 or fewer empty single-seat units remain in the row, the rule is waived to avoid a completebooking deadlock.2. Seats (or seat-pairs) at the physical ends of a row are checked on one side only.3. Physically blocked seats (broken or obstructed) are treated as occupied for the purpose of thiscalculation.4. A paired seat unit adjacent to another paired seat unit is evaluated as two adjacent blocks — nosingle-seat gap can exist between two pair boundaries by construction, since each pair occupiesexactly 2 contiguous columns.Applies to: UC10, UC16.</td></tr><tr><td colspan="1" rowspan="1">CBR-03</td><td colspan="2" rowspan="1">Concurrent Seat Selection: When two users attempt to select the same seat simultaneously, the systemguarantees that only one request succeeds. The second request receives an immediate conflictnotification without creating any inconsistent state. The seat map reflects status changes in near real-time to minimize the likelihood of simultaneous selection conflicts. Applies to: UC10, UC16.</td></tr><tr><td colspan="3" rowspan="1">CBR-04          Age RestrictionThe system enforces age-based access control for all restricted-rated films according to Vietnamesecinema classification. Two restriction types apply:• K: Children under 13 are permitted to watch only when accompanied by a verified adult guardian.• T13 / T16 / T18: Minimum age 13 / 16 / 18 respectively. Access is blocked for customers belowthe minimum age regardless of accompaniment.Definition of "Verified Adult Guardian" (for K-rated films):A "verified adult guardian" is defined as an individual aged 18 years or older at the time of the showtime.The guardian's age must be verifiable via a government-issued photo ID (CCCD/CMND or Passport)presented at the check-in counter.Online (UC-09, UC-10):• T13 / T16 / T18: System validates the Customer's Date of Birth stored in their profile against thefilm's minimum age requirement. If underage → booking is blocked with an error message. If DOBis not on record → system prompts the Customer to enter their date of birth before continuing;the entry is saved to the profile.• K: If the Customer's DOB indicates age under 13, the system displays a notice that an adultguardian must be present and requires a confirmation checkbox before proceeding. Thedeclaration is recorded in the booking record. (Online system trusts the declared DOB and doesnot require ID upload at this stage).Offline (Box Office - UC-16):• T13 / T16 / T18: Cashier must verify the customer's government-issued ID (CCCD/CMND) beforecreating the booking. POS displays a minimum age reminder for the current film.K: Cashier confirms that an adult guardian is physically present at the counter before completingthe booking. (ID verification for the guardian is deferred to check-in to reduce queue time, but the</td></tr><tr><td></td><td colspan="2">• K: Cashier verifies that an adult guardian is physically present alongside the child. The Cashier must request the adult guardian to present their government-issued ID (CCCD/CMND) to confirm they are ≥ 18 years old. If the guardian fails to present valid ID, is under 18, or is not present, entry is denied for the entire group (both adult and child). Failure Handling at Check-in (Age-Related Denial): If a booking fails check-in solely due to age verification failure (i.e., customer underage for T13/T16/T18 without valid ID, or no eligible adult guardian ≥18 accompanying a child for K), the following rules apply as an exception to CBR-05: 1. The booking is immediately cancelled. 2. 100% of the ticket price is refunded to the customer (this overrides the time-based refund percentages defined in CBR-05). 3. F&amp;B items (already in CONFIRMED status per BR-UC11-02) and any service fees are non- refundable.</td></tr><tr><td></td><td colspan="2">showtime already started → 0% refund. The following are non-refundable under all circumstances: F&amp;B items in CONFIRMED or FULFILLED status, and any service fees charged. Customers may only cancel an entire booking through the online channel; partial seat cancellation is handled exclusively at the counter by a Cashier. Refund Denial: Overrides standard policy) Denied check-in due to Age Rating mismatch or failure to present Student ID for online ticket without paying surcharge results in 100% ticket refund, 0% F&amp;B refund (items can still be collected), and 0% service fee refund. Applies to: UC19, UC22, UC23. Payment Timeout: Once a Customer confirms their order and is redirected to the payment gateway, the</td></tr><tr><td>CBR-07</td><td colspan="2">to EXPIRED status and all held seats are released. A FAIL callback within the window moves the booking to FAILED status with seats released. A SUCCESS callback confirms the booking and triggers the post- payment flow. Applies to: UC09, UC13. Loyalty Points Earning: Customers earn 1 loyalty point for every 10,000 VND spent on ticket purchases. Points are calculated on the actual ticket price after all discounts (vouchers and redeemed points) have been applied, using floor rounding (eg, 85,000 VND = 8 points). F&amp;B charges, service fees, and room surcharges are excluded. Points are credited to the account when the booking reaches CONFIRMED status. If a booking is subsequently canceled, the earned points are reversed (see CBR-13). For offline bookings, the Cashier must first identify whether the walk-in customer has a registered account by</td></tr><tr><td>CBR-08</td><td colspan="2">status. If no account exists, the booking is recorded without loyalty point association. Applies to: UC09, UC24, UC25. Cancellation Source Restriction: The channel through which a booking may be canceled is governed by its source field. Bookings with source = ONLINE may be canceled either online by the Customer or at the counter by a Cashier. Bookings with source = OFFLINE may only be canceled at the counter by a Cashier;</td></tr></table>

<table><tr><td>the Cancel option is hidden from the Customer's online booking history for OFFLINE bookings. The system evaluates the Booking.source field before rendering any cancellation controls. Applies to: UC15, UC22. CBR-09</td></tr><tr><td>Showtime Freeze: Once a showtime's scheduled start time is reached — evaluated using server time only - the system enforces a two-phase freeze: Immediately at start time:</td></tr><tr><td>• Ticket cancellation is blocked both online and at the counter. • Online ticket sales are closed.</td></tr><tr><td>• The Cinema Manager cannot edit showtime details or modify seat allocations. 15 minutes after start time: • Walk-in ticket sales at the box office (Cashier) are also closed. A 15-minute late-entry grace</td></tr><tr><td>period is permitted for offline sales only, acknowledging that pre-show advertisements typically run before the film begins. The following actions remain permitted at all times after the showtime has started:</td></tr><tr><td>• QR code check-in scanning by the Cashier. • Food order fulfillment by Concession Staff.</td></tr><tr><td>Applies to: UC09, UC16, UC22, UC28. CBR-10 Seat Type, Time-Slot &amp; Promotional Pricing: Ticket prices are calculated in four sequential steps:</td></tr><tr><td>Step 1 — Base price by time slot: A base price is selected according to the showtime's scheduled start time: Morning (before 12:00), Afternoon (12:00–17:59), or Evening (18:00 onwards). Weekend (Saturday and Sunday) and public holiday rates override the time-slot rate regardless of start time. The public</td></tr><tr><td>holiday calendar is configured by the System Admin in UC-35. Step 2 — Seat-type multiplier: The base price is adjusted by seat type, assigns a seat type from the active Seat Type Catalog: For example, Standard = base price × 1.0; VIP = base price × 1.5; Sweetbox = base price</td></tr><tr><td>× 2.0. This depends on Cinema Manager and business decisions. Step 3 — Premium room surcharge: A fixed surcharge is added for premium rooms (IMAX, 4DX, Dolby</td></tr><tr><td>Atmos), configured per room by the Cinema Manager in UC-30. This surcharge is excluded from all discount calculations. Step 4 — Promotional discounts: Discounts apply to the Step 2 price only. Three discount types are</td></tr><tr><td>evaluated: • Promotional group (only the single highest-value discount applies): Birthday — 20% off on the Customer's date of birth, auto-detected from profile (online) or looked up by phone number</td></tr><tr><td>promotional group discount above. C. Voucher: Applied after the above discounts if a valid code is entered (see CBR-11, CBR-12).</td></tr><tr><td>The combined total of all Step 4 discounts must not exceed 39% of the Step 2 price. If the combined total would exceed this cap, the voucher discount is reduced first until the total equals exactly 39%. If the voucher is reduced to 0% and the cap is still reached, the voucher code is not marked as used and remains valid for future bookings (BR-UC12-02) The final ticket price is locked at the moment the seat is locked (CBR-01). Any subsequent changes to pricing tables, surcharges, or promotional configurations do not affect in-progress bookings. F&amp;B charges, service fees, and room surcharges are excluded from all discount and loyalty point calculations. NOTE: 39% cap = regulatory/business decision to ensure minimum revenue per seat. Rationale: prevents stacking of Birthday (20%) + Online (10%) + Voucher (9%) = 39%. Step 5 — VAT (inclusive pricing): All prices displayed to the Customer are VAT-inclusive. The Customer pays exactly the displayed amount — no additional tax is charged at checkout. VAT is not a surcharge; it is Applies to: UC09, UC16, UC30. A maximum of one manually entered voucher code may be applied per booking. Attempting to apply a second code while one is already active will be rejected. Removing an applied voucher resets its discount and allows a new code to be entered.</td></tr><tr><td>embedded within the displayed price. However, the itemised receipt (UC-18) and booking confirmation (UC-14) must display a full VAT breakdown as follows: Line item VAT rate Breakdown shown on receipt Net ticket price + VAT 5% = displayed ticket Ticket(s) 5% price F&amp;B items 8% Net F&amp;B price + VAT 8% = displayed F&amp;B price</td></tr><tr><td>Room surcharge 5% Net surcharge + VAT 5% = displayed surcharge (IMAX/4DX/Dolby) 10% or cinema manager Net service fee + VAT 10%/or price set = Service fee (if applicable) set displayed fee Receipt VAT breakdown — calculation example: Ticket displayed price: 100,000 VNĐ (VAT-inclusive at 5%) → Net ticket price = 100,000 ÷ 1.05 = 95,238 VNĐ → VAT 5% = 4,762 VND F&amp;B displayed price: 50,000 VNĐ (VAT-inclusive at 8%) → Net F&amp;B price = 50,000 ÷ 1.08 = 46,296 VND → VAT 8% = 3,704 VND Total paid by Customer = 150,000 VNĐ Receipt shows: Net subtotal 141,534 VND + VAT 8,466 VND = 150,000 VND Discounts (Step 4) are applied to the VAT-inclusive displayed price. The VAT breakdown on the receipt reflects the post-discount amounts.</td></tr></table>

<table><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Regardless of how many tiers apply simultaneously, the combined total discount across all three tiersmust not exceed 39% of the Step 2 ticket price as defined in CBR-10. When the cap is reached, the Tier 3voucher discount is reduced first; if the cap is still exceeded after the voucher is zeroed out, the Tier 2campaign discount is reduced next. Tier 1 discounts are never reduced by the cap.Applies to: UC12, UC31.</td></tr><tr><td colspan="1" rowspan="1">CBR-12</td><td colspan="1" rowspan="1">Voucher Eligibility Validation: A voucher code is valid and applicable only when all of the followingconditions are simultaneously met: the code exists in the system; the current date/time falls within thevoucher's validity period; the total redemption count has not reached the defined maximum; theCustomer's account has not previously used this code; and all optional scope restrictions defined on thevoucher are satisfied, including applicable movies, time slots, days of the week, seat types, and minimummembership tier. Validation is performed twice: once immediately when the code is entered, and again atpayment confirmation, since order details may change between the two points.Applies to: UC12, UC31.</td></tr><tr><td colspan="1" rowspan="1">CBR-13</td><td colspan="1" rowspan="1">Loyalty Points Reversal on Cancellation:When a booking is canceled and loyalty points were previously earned from that booking, the systemdeducts the corresponding points from the Customer's current balance. Under normal circumstances thebalance will always cover the deduction; however, if the Customer has redeemed points from otherbookings in the interim and the current balance is insufficient, the balance is set to zero and the shortfallis logged for audit purposes.Full cancellation: The entire amount of points originally earned from the booking is reversed in full,regardless of the money refund amount. A 0% money refund (e.g. late cancellation) still triggers a fullpoints reversal.Partial cancellation (Cashier at counter only, per CBR-05): The points reversal is calculated proportionallybased on the ratio of canceled seats to the total number of seats in the original booking, applied to thepoints originally earned. For example, if a 4-seat booking earned 40 points and 2 seats are canceled, 20points are reversed.Redeemed points reinstatement: If the Customer had redeemed loyalty points as a discount on thecanceled booking (per UC25), those redeemed points are reinstated to the Customer's balance uponcancellation. For partial cancellations, only the portion of redeemed points proportional to the canceledseats is reinstated.All reversal and reinstatement entries appear in the Customer's points history with the following labels:• Reversal: "Points reversed — booking cancellation [booking_id]: -X points."• Reinstatement: "Points reinstated — booking cancellation [booking_id]: +X points."Applies to: UC22, UC24.</td></tr><tr><td colspan="1" rowspan="1">CBR-14</td><td colspan="1" rowspan="1">QR Code Validity: Each booking confirmation generates a unique QR code containing the booking ID and adigital signature to prevent tampering and forgery. At check-in, the system validates the QR code againstfour conditions: the digital signature must be authentic; the booking must be in CONFIRMED status; theshowtime date must match the current date; and the booking must not have been previously checked in.If any condition fails, check-in is rejected with a specific error message indicating the reason. Uponsuccessful check-in, the booking is marked CHECKED_IN and the QR code is immediately invalidated toprevent reuse. Applies to: UC14, UC19.</td></tr><tr><td colspan="1" rowspan="1">CBR-15</td><td colspan="1" rowspan="1">OTP Validation: OTPs used for account registration and password reset consisting of 6 randomlygenerated digits and expire 5 minutes after issuance. A maximum of 3 incorrect attempts are allowed perOTP; exceeding this limit invalidates the OTP immediately and requires a new one to be requested. Usersmay request a new OTP up to 3 times within any 15-minute window to prevent spam notification. Eachnew OTP request immediately invalidates any previously issued OTP for the same action, ensuring onlythe latest code is active. An OTP is also invalidated upon successful use and cannot be reused.Applies to: UC01, UC04.</td></tr><tr><td colspan="1" rowspan="1">CBR-16</td><td colspan="1" rowspan="1">Room Maintenance Lock: A screening room in MAINTENANCE status is subject to the followingrestrictions: no new showtimes may be scheduled for that room; any existing upcoming showtimes in the</td></tr><tr><td>CBR-17</td><td>room have their seat maps fully blocked, preventing new ticket sales. The Cinema Manager retains the ability to edit the room's seat layout configuration during the maintenance period. When the room status is changed back to ACTIVE, any previously created upcoming showtimes automatically resume ticket sales. Before setting a room to MAINTENANCE, the system checks for upcoming published showtimes in that room and displays a warning if any exist. If any seats are currently locked under an active session (CBR-01) at the time the room is set to MAINTENANCE, those sessions are immediately terminated and the locked seats are released. Applies to: UC28, UC29. Audit Logging:</td></tr><tr><td></td><td>of the following business events occurs: a user performs a data-modifying action (including creating, updating, or deleting system data); an administrator alters critical system configurations or permissions; a user triggers a financial transaction or reversal (such as ticket cancellations or refunds); or a security-sensitive event occurs (such as password resets or account lockouts). The generated log entry must capture an event record to be displayed directly on the system log interface, which simultaneously includes: the precise date and time of execution; the account identity of the initiating actor; the specific role of that actor; the associated Use Case ID; the action type; the affected target data object; the final execution status (Success or Failure); and a detailed payload text describing the specific changes made. Once written, audit log records are strictly read-only and cannot be modified or deleted by any user level, including system administrators. Applies to: UC-02, UC-04, UC-05, UC-21, UC-22, UC-26, UC-28, UC-29, UC-31, UC-34, UC-35</td></tr></table>

## 4. Mockups Screen

This section contains the screens and their respective attributes associated with one or more use cases defined in Use Case Specifications section above.

SC001: Homepage (Zone 1)

![](images/812a9ad907d8b79859a4136791d6788ba6294c6c19e445c19756a4f61b7fc300.jpg)

CINESTAR \*

AVATAR: THE WAY <OF WATER

Sci-Fi Action Adventure

T13 ⑤3h 12m ★ 7.8/10

Xem Trailer Đt vé ngay

![](images/190cb02995312c0bcd455df30947752698eaaebabec3b1848c8708837f051e26.jpg)

Chon rap / Thành ph Hóm nay T3 17/6 T4 18/6 T5 19/6 T6 20/6 T7 21/6 CN 22/6

Th loi  Ngôn ngū Loi phòng  Sut chieu   Xoá filter

![](images/9239bbe8e0b04a530febc849c82f42307e9202469418d60208d118ffdb4428c0.jpg)

![](images/e05af3277ab80249b9719da7405787346b03b8f396a492aba3c4ff41a38d1be3.jpg)

![](images/2303641e84c9576d3f2d73c161de3d3e9ce34ac5bfd434f889b8f1eeb437c4de.jpg)

![](images/5cb9345c0deff88795b35f61ead5c21601ed3409c3bd7d3dab2135c56994c03e.jpg)

![](images/03232fb9617bdd908efcc22712ef4e51ff6b922a4165b59ce3d4a2a455f5dba5.jpg)

Đt Vé Nhanh

![](images/49f524e601c6a482cab3b87acebec6e497ac218221970a61382b94eb09fa3180.jpg)

![](images/18452b582e0f5f0e69417e92772686a290fdbd72d6a9529b2a423b6bbf9b9db9.jpg)

Đt vé ngay

![](images/6222c0dd74d1f6ade0fcc1d187a661e55774b7752fd8ea9b98abfb5e18351b7f.jpg)

Tri nghim đin ánh đinh cao

CINESTAR ★

VÉ CINESTAR   
Gii thiu v chúng tôi H thőng rap chiu   
Tuyén dung   
Điu khoán s dung

123 Nguyn Hu, Q1, TP. HCM 1800 1234 (Miěn phí) support@cinestar.vn

HÔ TRO KHÁCH HANG Cu hói thưng gāp Chính sách đi / trá vé Hưng dn đät vé Chưong trinh diém thưng

![](images/558c5b17683bc76557661b857e2026d6d72829081db43e4bed1a023771afbfa5.jpg)

9 回 □ x

©2026 CineStar.All rights reserved.

![](images/187d74588a041c1f9cbe3f638fdbadb910ebeebd775f5de7d053a1a2bbbe7fac.jpg)

<Screenshot>  
SC001: Homepage
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Hero Slider</td><td rowspan=1 colspan=1>Hero slider – automation or slide when user click the arrow</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Movie Grid Layout</td><td rowspan=1 colspan=1>Movie Grid Layout is separated to 2 tabs: Phim đang chiu, Phim såp chiu</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Birthday Banner</td><td rowspan=1 colspan=1>A birthday banner suggest user verify CCCD for discount at their birthday</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>Header navbar</td><td rowspan=1 colspan=1>Include logo, search bar and login button</td></tr></table>

## SC002: Login (Zone 1)

CINESTAR ★

Đăng nhp Tri nghim đin nh đinh cao

EMAIL

ban@email.com

MÂT KHÃU

Quên mt khu?

Đăng nhp

hoc

G Đăng nhp vi Google

Chí dành cho khách hàng

Chưa có tài khon? Đăng ký ngay

SC002: Login
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Form</td><td rowspan=1 colspan=1>Email + Password</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Login zone</td><td rowspan=1 colspan=1>Login button, link ‘Quên mt khu&#x27;, “Đăng kí”</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Google Oauth button</td><td rowspan=1 colspan=1>Google Oauth button for login through Google</td></tr></table>

SC003: Register (Zone 1)

![](images/5b888fb9c259158fa5f4a4d24c11129886299d7feca700da8db735ce9ca60ee3.jpg)

<Screenshot>

SC003: Register

<table><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Hero paris vibe</td><td rowspan=1 colspan=1>Eiffel doodle, marquee CINESTAR</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Form</td><td rowspan=1 colspan=1>H tên, Email, SĐT, Mt khu, Xác nhn mt khu</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Register button</td><td rowspan=1 colspan=1>Button ‘Đăng kí, link back to Login page</td></tr></table>

SC004: Reset Password (Zone 1)

![](images/690d9daba7ccce613ebcbce55826933b73dfa1c0b11a37956891f5f85438b306.jpg)

<Screenshot>  
SC004: Reset Password
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Form</td><td rowspan=1 colspan=1>Email, “Phương Thc Thanh Toán”</td></tr></table>

SC005: Movie Detail (Zone 1)

![](images/0df16068ec9242060fbfb49e80555369a96f77075b82f526ce305f2e0f15eb49.jpg)

![](images/774c5bc1f3bb1fcfc5c52dbf820a09f73aa9d0d5ab5a6ed00b7bfc51211eb74e.jpg)

![](images/3b087de0c4fd8e93b74cd65a27836d1862fcd7028c0b5d4a8f6edd18b1874559.jpg)

![](images/dca05f118014cb5f572ae04257efa811ae75ec54deb0088e30a90892c37dab6d.jpg)

Superhero ActionT16

# VENOM: THE LAST DANCE

1h 49m USA 05/06/2026 ★7.2/10 (612 đánh giá)

![](images/96e7e645460a2aeae82144dbfa8c9f518176e25d77b8154a3b6847d386f576c0.jpg)

Phim này dành cho khán gi t 16 tui tr lên. Vui lòng xác nhn đ tui trưc khi đt vé.

![](images/437346bbc3a2ec5189fc1433bf3215e0fad48692773de15e5ddf7f73020fd2ff.jpg)

![](images/d8d00eaf457251a977ac069f5c8ca8a3875635c50d2521b89d7e92793bbcd14b.jpg)

![](images/2e23495597b8aa3dd26c52dac5f250ee26dbe0132896c8defe64f98158aaab44.jpg)

![](images/3c55d452b38a4e2ac17481b8a9727f3de063f3ba420bfaab83326141b37547d6.jpg)

Today Tue 17/6 Wed 18/6 Thu 19/6

IShowtimes

3\*\_

3D  Subtitled

7.2   
612 đánh giá

1★一

Screen 05 10:10 90 / 90 seats

15:50 seat

Edit with  Lovable ×

11:50 seal

Screen 07 13:50 7/120 seat

Screen 05 16:40 90 seats

2D  Subtitled

20:45

Screen 06   
20:30

Screen 0718:00/120 seat

22:1010

khoatran92 k

Phim quá tuyt vi! Hiu ng đinh cao, ct truyn hp dn.

★★★★★

honganh.le

Tri nghim IMAX rt đáng giá, âm thanh sng đng.

★★★★

## CINESTAR ★

VÊ CINESTAR

Tri nghim đin ành đinh cao

Gii thiu vě chúng tôi

HÕ TRO KHÁCH HÀNG

H thng rap chiu

Câu hi thưng gp

KÉT NI VI CHÚNG TÔI

![](images/803c033850d54be5734246329b1643eb7f6d16c4ee03be94740bc064ed4ec3f6.jpg)

Chính sách đi / trà vé

![](images/d12c7295dd841a47cf620e0d4e1adb9cbe9dd51a09154cd40a0d90873fbb1555.jpg)

123 Nguyn Hu, Q1, TP. HCM

F © □ X

Tuyn dung

1800 1234 (Min phi)

support@cinestar.vn

Hưng dn đät vé

Điu khon s dung

Chương trinh đim thưng

© 2026 CineStar. All rights reserved.

Điu khoán Cookie Bán đö trang

## <Screenshot>

SC005: Movie Detai

<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Top content</td><td rowspan=1 colspan=1>Big poster + information of the movie</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Trailer embed</td><td rowspan=1 colspan=1>Trailer of the movie</td></tr></table>

Displays showtimes for that movie  
![](images/599104561c4ff08c953c5a78f435d0ae953ed013cd4166094f2e62aa84a883f7.jpg)

<Screenshot>  
SC006: Seat Map (Booking Flow)
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left main content</td><td rowspan=1 colspan=1>Seat map</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Right main content</td><td rowspan=1 colspan=1>Temporary receipt</td></tr></table>

SC007: F&B (Booking Flow) (Zone 1)

![](images/e08f37c796ef5d416831450fd235d5f6a40b9b16fb1797e645e4f3aa19bb38e1.jpg)

<Screenshot>  
SC007: F&B (Booking Flow)
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Combo Tab</td><td rowspan=1 colspan=1>Category tabs of food</td></tr></table>

SC008: Voucher (Booking Flow) (Zone 1)  
![](images/95720f955da039c3c3330b9730f4e994b99c30c1a1ce886872245a2403726272.jpg)

<Screenshot>  
SC008: Voucher (Booking Flow)
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Voucher Input block</td><td rowspan=1 colspan=1>Customer enter the voucher they want to input for discount</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Loyalty Point RedeemingSlider</td><td rowspan=1 colspan=1>Customer slides the slider for choosing range of discount</td></tr></table>

## SC009: Payment (Booking Flow) (Zone 1)

![](images/6a9ebcd8d285a1b58012eb07a50842d495f01844d039c92ba674891415117957.jpg)

<Screenshot>  
SC009: Payment (Booking Flow)
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left main content</td><td rowspan=1 colspan=1>Breakdown: price, surcharge, online discount, voucher...</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Right main content</td><td rowspan=1 colspan=1>Payment Method</td></tr></table>

SC010: Confirmation (Booking Flow) (Zone 1)

![](images/fc5ba99faf701aa67e050ac82580f83d3f2c358957eba0b254968fe205fa6d18.jpg)

<Screenshot>  
SC010: Confirmation (Booking Flow)
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Main content</td><td rowspan=1 colspan=1>E-ticket, movie information, detail VAT</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Other component</td><td rowspan=1 colspan=1>Button “V trang ch”, “Ti v”</td></tr></table>

SC011: Loyalty Points Redeeming (Zone 1)

khoatran92 nguyenql@gmail.com

Lich s đt vé

8 Thông tin cá nhân

Đim thưng

<table><tr><td rowspan=1 colspan=1><img src="images/26eef649c3d621b644274b7e1db5ef1c5e4085c7862a142ba4889e662de78147.jpg"/></td></tr><tr><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td></tr></table>

123 Nguyn Hu, Q1, TP. HCM

Điëu khoán Cookie Bán đö trang

<Screenshot>  
SC011: Loyalty Points
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Right content</td><td rowspan=1 colspan=1>Current loyalty point, loyalty transaction</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Left content</td><td rowspan=1 colspan=1>Customer badge + tabs</td></tr></table>

## SC012: Profile (Zone 1)

![](images/a52537854bb1cc1c05c3c160bfc2c02a00193ec53c236ee3cd589ab16355accf.jpg)

<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>H tên, SĐT, Email, Đi mt khu</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Left Content</td><td rowspan=1 colspan=1>Customer badge + tabs</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Status Badge</td><td rowspan=1 colspan=1>Verified or not yet</td></tr></table>

SC012: Profile

<Screenshot>

SC013: Booking History (Zone 1)  
![](images/7366a957287f7051cb538c2c062b9a586ab78ce104a58673789723a41ca92366.jpg)

<Screenshot>  
SC013: Booking History
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Right Content</td><td rowspan=1 colspan=1>Movie booked separated into tabs: Såp chiu, Đã xem, Đã hy with information info,button “Xem QR” and button “Hy vé”</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Left Content</td><td rowspan=1 colspan=1>Customer badge + tabs</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr></table>

SC014: AI Chat Box (Zone 1)

![](images/98274ec01ad10b26f4ef0ec7b70f399865c0e4263f677a9dc0cf14ad101f0aef.jpg)

<Screenshot>  
SC014: AI Chat Box
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>Al Chat Box Content, Clickable Sugger, Send Button</td></tr></table>

SC015 + SC016: CCCDVerify (Zone 1)  
![](images/2b57637c97277c84ceb5e2f93af031c0062f02105ae94d1da0a2c745fe948df7.jpg)

![](images/85fac652b5b2b93026a845d23051aa0edae2bbedce411bf6e63ffbbd490b0546.jpg)

<Screenshot>
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>Introduction why we need eKYC, steps information, Button “Bt đu xác thc”</td></tr></table>

## SC017: Select Movies And Showtimes (Zone 2)

<table><tr><td>SC-P01·UC-16 SELECT MOVIE &amp; SHOWTIME</td></tr><tr><td>Search movies, showtimes, room...</td></tr><tr><td>Shift: POS Showtimes Seats F&amp;B Payment Print Check- Cancel CINESTAR 14:00- khoatran92 Logout Dashboard in 22:00 Oppenheimer</td></tr><tr><td>2D 03 17:30 CLOSED 12/150 Unavailable Drama·History· T18 Venom: The Last Dance 2D 03 19:45 Δ Grace · 8 min left 23/150 Select → Superhero·Action·T16</td></tr><tr><td>Avatar: The Way of Water IMAX 01 20:15 PUBLISHED 45/200 Select → Sci-Fi·Action·T13</td></tr><tr><td>Inception 3D 02 20:30 SOLD OUT 0/120 Unavailable Sci-Fi · Thriller · T16</td></tr><tr><td>The Batman Dolby 04 21:00 PUBLISHED 88/140 Select → Action·Crime·T16 Dune: Part Two IMAX 01 22:30 PUBLISHED 178/200 Select → Sci-Fi·Drama·T13</td></tr><tr><td>Tip: T18 ratings require ID verification at the counter. Scan QR Check-in Cancel ticket Edit withLovable ×</td></tr></table>

## <Screenshot>

SC017: Select Movies And Showtimes
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Header/page title</td><td rowspan=1 colspan=1>SELECT MOVIE &amp; SHOWTIME</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Search bar</td><td rowspan=1 colspan=1>Input to search room, movie, showtime</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Showtime table</td><td rowspan=1 colspan=1>Include column: Movie, Rooom, Time, Status, Seats, Action and a small poster of themovie</td></tr></table>

## SC018: Seats (Zone 2)

![](images/1382f1ffe1d860ae54382612f4c31b755a505b9eb7dd2f5af5ed7b2cbe727542.jpg)

<Screenshot>

SC018: Seats

<table><tr><td colspan="1" rowspan="1">#</td><td colspan="1" rowspan="1">Component</td><td colspan="1" rowspan="1">Description</td></tr><tr><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">Header</td><td colspan="1" rowspan="1">SELECT SEATS</td></tr><tr><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">Movie info card</td><td colspan="1" rowspan="1">Poster, movie name, room, age rating</td></tr><tr><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">Member lookup bar</td><td colspan="1" rowspan="1">Input phone/member ID + button “Lookup" + display loyalty point and checkboxstudent discount</td></tr><tr><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">Seat Map</td><td colspan="1" rowspan="1">Seat Grid Layout</td></tr></table>

SC019: F&B And Voucher (Zone 2)  
![](images/d7ed6deffb51247bdae78894e25d1473349f841470449544ad5fe439b372a29d.jpg)

<Screenshot>  
SC019: F&B And Voucher
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Header</td><td rowspan=1 colspan=1>F&amp;B &amp; VOUCHER</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Category Tabs</td><td rowspan=1 colspan=1>Food separated to category tabs</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Product</td><td rowspan=1 colspan=1>Card for each product</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>Order summary Sidebar</td><td rowspan=1 colspan=1>Voucher input + Apply, Confirm and Pay</td></tr></table>

SC020: Payment (Zone 2)  
![](images/d3f952469cd6838f7970fc941b6bd0e933b4ab47b16741f45fc2ab0791399cb1.jpg)

<Screenshot>  
SC020: Payment
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Header</td><td rowspan=1 colspan=1>PROCESS PAYMENT</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Payment Method card</td><td rowspan=1 colspan=1>Cash/Card/QR Transfer</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Cash panel</td><td rowspan=1 colspan=1>Input Customer gives, “Confirm each received&quot; button</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>Card panel</td><td rowspan=1 colspan=1>Spinner + “Waiting for POS termial...&quot; + Retry/Change Method</td></tr><tr><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>QR panel</td><td rowspan=1 colspan=1>Huge QR with CINESTAR logo at the center</td></tr><tr><td rowspan=1 colspan=1>6</td><td rowspan=1 colspan=1>Invoice SummarySidebar</td><td rowspan=1 colspan=1>Booking code, movie information, price breakdown, discount voucher, notes</td></tr></table>

SC021: Print Physical Ticket (Zone 2)  
![](images/f352907e96153a2371f0d29e10d0d2ca801ab9f809f43750ac8919d03a7cecb5.jpg)

<Screenshot>  
SC021: Print Physical Ticket
<table><tr><td colspan="1" rowspan="1">#</td><td colspan="1" rowspan="1">Component</td><td colspan="1" rowspan="1">Description</td></tr><tr><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">Header</td><td colspan="1" rowspan="1">PRINT TICKETS &amp; RECEIPT</td></tr><tr><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">Ticket cards</td><td colspan="1" rowspan="1">A ticket card include CINESTAR logo + movie information, showtime information,booking code, QR HMAC-signed</td></tr><tr><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">Receipt card</td><td colspan="1" rowspan="1">Price breakdown</td></tr><tr><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">Action button</td><td colspan="1" rowspan="1">Button “Print tickets &amp; receipt”, button “Sell another”</td></tr></table>

SC022 Check-in (Zone 2)

<Screenshot>  
![](images/2e06e82e38936c8db66ee6c24cfe3b93f24ac72c33717d3bc2c499e5c971b19b.jpg)

<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Header</td><td rowspan=1 colspan=1>CHECK-IN</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Scanner viewfinder</td><td rowspan=1 colspan=1>300 x 300 px with 4 angels accent, laser scan line animate</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Manual Input</td><td rowspan=1 colspan=1>Input booking code + button “Verify”</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>Cashier deny bar</td><td rowspan=1 colspan=1>Deny Check-in with reasons dropdown</td></tr><tr><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Demo Result button</td><td rowspan=1 colspan=1>Status: success, err-sig, err-cancel, err-day, err-used, err-age</td></tr></table>

SC023: Cancel (Zone 2)

![](images/f3fe132b6886181ad1ade93e777f0c98d59c19aee68c32595a99a9d9a111c71a.jpg)

<Screenshot>  
SC023: Cancel
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Header</td><td rowspan=1 colspan=1>CANCEL TICKET AT COUNTER</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Process steps</td><td rowspan=1 colspan=1>4 steps: Find booking =&gt; Cancel Type =&gt; Refund calculation =&gt; Process refund</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Action buttons</td><td rowspan=1 colspan=1>Button “Confirm canceelation&quot;, button Abort</td></tr></table>

SC024: Order Queue Screen (Zone 3)  
![](images/1e37a476b8d5831b84659301f91e98c16aafa7928bc4fb049f824125cadef9e8.jpg)

<Screenshot>  
SC024: Order Queue Screen
<table><tr><td>#</td><td>Component</td><td>Description</td></tr><tr><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">Header</td><td colspan="1" rowspan="1">CINESTAR logo, label “Concession Counter", real-time timer</td></tr><tr><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">F&amp;B Order cards grid</td><td colspan="1" rowspan="1">3 column, each card = 1 column with information: bookingld, room + showtime, check-in time, seats, items list</td></tr><tr><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">Elapsed timer</td><td colspan="1" rowspan="1">Waiting: Xm:Xs</td></tr><tr><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">Action buttons</td><td colspan="1" rowspan="1">Button “Complete”, Partial”. There are no button “Cancel”</td></tr></table>

SC025: Dashboards (Zone 4)

<table><tr><td colspan="2">Top movies (today)</td><td>All →</td></tr><tr><td>#1</td><td>Avatar: The Way of Water Sci-Fi·Action</td><td>420 TIX</td></tr><tr><td>#2</td><td>Inception Sci-Fi·Thriller</td><td>360 TIX</td></tr><tr><td>#3</td><td>Venom: The Last Dance Superhero·Action</td><td>300 TIX</td></tr><tr><td>#4</td><td>Dune: Part Two Sci-Fi·Drama</td><td>240 TIX</td></tr></table>

<table><tr><td>Recent bookings Edit withLovable</td></tr><tr><td>CIN- Avatar: The Way of 377,000 d Water PAID A7X9</td></tr><tr><td>CIN- 289,000 B4K2 The Batman PAID a</td></tr><tr><td>CIN- Venom: The Last Dance 120,000 đ C2P1 REFUND</td></tr><tr><td>CIN- Dune: Part Two 199,000 d D9M5 PAID</td></tr><tr><td>CIN- Inception 100,000 đ HOLD E6L7</td></tr></table>

<table><tr><td colspan="6">Today&#x27;s showtimes Movie Room Time Status Sold</td></tr><tr><td>Avatar: The Way of Water</td><td>IMAX 01</td><td>20:15</td><td>PUBLISHED</td><td>155/200</td><td>Action Edit</td></tr><tr><td>Inception</td><td>3D 02</td><td>20:30</td><td>SOLD OUT</td><td>120/120</td><td>Edit</td></tr><tr><td>Venom: The Last Dance</td><td>2D 03</td><td>19:45</td><td>GRACE</td><td>127/150</td><td>Edit</td></tr><tr><td>Dune: Part Two</td><td>IMAX 01</td><td>22:30</td><td>PUBLISHED</td><td>22/200</td><td>Edit</td></tr><tr><td>The Batman</td><td>Dolby 04</td><td>21:00</td><td>PUBLISHED</td><td>52/140</td><td>Edit</td></tr><tr><td>Oppenheimer</td><td>2D 03</td><td>17:30</td><td>CLOSED</td><td>138/150</td><td>Edit</td></tr><tr><td colspan="6"></td></tr></table>

<Screenshot>  
SC025: Dashboard
<table><tr><td colspan="1" rowspan="1">#</td><td colspan="1" rowspan="1">Component</td><td colspan="1" rowspan="1">Description</td></tr><tr><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">Sidebar</td><td colspan="1" rowspan="1">Login CINTESTAR, navbar (depends on Cinema Manager or Admin role)</td></tr><tr><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">User Profile (clickable)</td><td colspan="1" rowspan="1">Avatar, username, role (Cinema Manager or Admin)</td></tr><tr><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">Header</td><td colspan="1" rowspan="1">DASHBOARD</td></tr><tr><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">KPI Cards</td><td colspan="1" rowspan="1">KPI Card: Revenue Today, Tickets Sold, Occupancy, F&amp;B Attach Rate</td></tr><tr><td>5</td><td>Other information blocks</td><td>Today's movies, Today's showtime, recent bookings</td></tr></table>

SC026: Movie Catalog (Zone 4)

![](images/21a192279ae6d193a04610f8e4c4e0106cad36e68563f1c6dbac2ab43eb5b240.jpg)

<Screenshot>

SC026: Movie Catalog
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left menu</td><td rowspan=1 colspan=1>Side bar menu</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>Grid card of movies: poster, title, status badge (Now showing / Coming soon / Draft)</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Filter / Search</td><td rowspan=1 colspan=1>Search box</td></tr></table>

SC027: Showtimes Scheduler (Zone 4)

![](images/692c05821e62566786818905f96c1b4fb31213e372d5e76780180a3f477a31f5.jpg)

<Screenshot>

SC027: Showtimes Scheduler

<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left menu</td><td rowspan=1 colspan=1>Side bar</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>Grid room x time of each showtime</td></tr></table>

## SC028: Pricing Matrix (Zone 4)

![](images/1f1c65660a8a8e0eb293b36abefeac255ad550bb91c3b3a1940e8b2a8c2c0952.jpg)

<Screenshot>  
SC028: Pricing Matrix
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left menu</td><td rowspan=1 colspan=1>Side bar menu</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>seat-type price: tier x base price x multiplier, day-type multiplier ,surcharge</td></tr></table>

SC029: View Vouchers And Promotions (Zone 4)

<table><tr><td>CINESTAR CINEMA MANAGER</td><td colspan="4">SC-M05·UC-26 VOUCHERS &amp; PROMOTIONS</td></tr><tr><td>Cinema CineStar District 7</td><td colspan="2">ACTIVE CAMPAIGNS 5</td><td colspan="2">TOTAL REDEMPTIONS TODAY DISCOUNT GIVEN (TODAY)</td></tr><tr><td>品 Dashboard 日 Movies</td><td colspan="2">312</td><td colspan="2">3.8MD</td></tr><tr><td>曲 Showtimes</td><td colspan="4">All Active Scheduled Expired Search code...</td></tr><tr><td>$ Pricing</td><td colspan="4">Code Description Usage Expires Status</td></tr><tr><td>H Vouchers 山 Reports</td><td colspan="4">15% off any 1,284 1 SUMMER2026 31/08/2026 ACTIVE showtime 5,000</td></tr><tr><td>目 Rooms 口 Seat Types</td><td colspan="4">20% off with STUDENT 642/∞ 31/12/2026 ACTIVE valid ID</td></tr><tr><td rowspan="4">F&amp;B Menu phamquynh Cinema Manager</td><td colspan="4">Free combo 188/ BIRTHDAY Always 1,000 ACTIVE upgrade</td></tr><tr><td>10% off 4+ 421/ FAMILY4 tickets 2,000</td><td>30/09/2026</td><td>Edit ACTIVE Disable</td></tr><tr><td>25% off Fri FLASHFRIDAY 9pm+</td><td>0/500 26/06/2026</td><td>SCHEDULED Edit withLovable</td></tr><tr><td>50,000đ off first WELCOME booking</td><td>3,420 / 31/12/2026 ∞</td><td>Edit ACTIVE Disable</td></tr><tr><td>OLDIES Senior 30% off</td><td>expired 97/500 31/05/2026</td><td>Edit EXPIRED Disable</td></tr></table>

<Screenshot>  
SC029: View Vouchers And Promotions
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left menu</td><td rowspan=1 colspan=1>Side bar menu</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>List campaign: code, discount, usage, status</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Action</td><td rowspan=1 colspan=1>&quot;New campaign” button</td></tr></table>

SC030: Reports (Zone 4)

![](images/6fcdf39c8b6ad3bb0e957a102333b3b11c12b3cd706ebb30e108898984e878b7.jpg)

<Screenshot>

SC030: Reports

<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Header</td><td rowspan=1 colspan=1>REPORTS</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Sidebar</td><td rowspan=1 colspan=1>Login CINTESTAR, navbar (depends on Cinema Manager or Admin role)</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>User Profile (clickable)</td><td rowspan=1 colspan=1>Avatar, username, role (Cinema Manager or Admin)</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>KPI Cards</td><td rowspan=1 colspan=1>KPI Cards: Week Revenue, Tickets, AVG Ticket Price, Refund Rate</td></tr></table>

SC031: Add Movie (Zone 4)

![](images/6ddaccd42e81511371d6d2eb6b112777c92d9f5c6341f9aa5def1cef32d7c532.jpg)

<Screenshot>  
SC031: Add Movie
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left menu</td><td rowspan=1 colspan=1>Side bar meny</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>Form: poster upload, title, duration, genre, release date, synopsis, statusDraft/Published</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Action</td><td rowspan=1 colspan=1>Button “Save movie”</td></tr></table>

SC032: Edit Movie (Zone 4)

![](images/6a578ae524bc947dee66d371bfe2e3dd34481a00a0fdd9c8ca4ac583e576f5a0.jpg)

<Screenshot>

SC032: Edit Movie
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left menu</td><td rowspan=1 colspan=1>&lt;Describe all links in the left menu&gt;</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>Form pre-filled movie information; its look like Add Movie but pre-filled information</td></tr></table>

SC033: Import Movie From TMDB (Zone 4)

![](images/5165cddc528060c7120f73a57cdcde276739810a93a024dd6d185155be4af00e.jpg)

## SC034: Manage Seat Type (Zone 4)

<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left menu</td><td rowspan=1 colspan=1>Side bar menu</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>Search bar TMDB; result list: poster, title, year, “Import&quot; button</td></tr></table>

SC033: Import Movie From TMDB

<Screenshot>

![](images/d7d6295804f1935a88dab7b59f5e8d2766c2f6ba2b063855cbb38fa44f2a7065.jpg)

<Screenshot>  
SC034: Manage Seat Type
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left menu</td><td rowspan=1 colspan=1>Side bar menu</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>List seat types: Standard, VIP, Sweetbox, Accessible; multiplier + color</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Actions</td><td rowspan=1 colspan=1>Add / Edit / Delete seat type</td></tr></table>

## SC035: Add New Room (Zone 4)

![](images/d02df71e21fd701f99b9b48e2702ae195efcb27ed81032c154166b2fc5163002.jpg)

<Screenshot>  
SC035: Add New Room
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left menu</td><td rowspan=1 colspan=1>Side bar menu</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>Grid seats: 4-way screen orientation, drag-paint seat types</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Special Lane</td><td rowspan=1 colspan=1>Sweetbox lane (couple seats, auto pair), Tech lane (exit sign, aisle light)</td></tr></table>

SC036: Add New Showtime (Zone 4)  
![](images/2fc26494ddee4dceedc5f5cf1e7f1cfe2a1a13f2416c7099ed392212d5236133.jpg)

<Screenshot>  
SC036: Add New Showtime
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left menu</td><td rowspan=1 colspan=1>Side bar menu</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>Form: dropdown for Room, dropdown for Movies ,start time, auto end-time, previewprice</td></tr></table>

SC037: Manage F&B Menu (Zone 4)  
![](images/50482da5bf10475614cdcf990a05698d01553871009d35798d9bf9c2ee1dc7f2.jpg)

<Screenshot>  
SC037: Manage F&B Menu
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left menu</td><td rowspan=1 colspan=1>Side bar menu</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Filter Tabs</td><td rowspan=1 colspan=1>All, Popcorn, Drinks, Combos</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>Card grid: Food picture, name, price, status Available/Out of stock</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>Add Model</td><td rowspan=1 colspan=1>Dialog: name, price, category, description, upload image</td></tr></table>

![](images/4687df1c55cf1b2a41c83d6fbfdaee5fe9583a319528b1465935e778dfd9c10f.jpg)

SC038: Add new campaign
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Left menu</td><td rowspan=1 colspan=1>Side bar menu</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Main Content</td><td rowspan=1 colspan=1>Form: campaign name, tier 2/3, batch codes, discount cap 35%</td></tr></table>

<Screenshot>

SC039: Account Management (Zone 5)  
![](images/b174bd0ec7302457b2589e193270bfcb8edd49b73f3c4f15222cfa465143b6bd.jpg)

<Screenshot>  
SC039: Account Management
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>User Profile</td><td rowspan=1 colspan=1>Avatar, username, role (Cinema Manager or Admin)</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Side bar</td><td rowspan=1 colspan=1>Navbar: menu content</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Search and Filter box</td><td rowspan=1 colspan=1>Admin can search, filter for account list range; Box include “Export CSV” button</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>Account List Box</td><td rowspan=1 colspan=1>Include Account information: Username, email, role, cinema, status, last login, actions(Edit, Lock)</td></tr><tr><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Header</td><td rowspan=1 colspan=1>ACCOUNTS &amp; ROLE</td></tr></table>

SC040: Create or edit account (Zone 5)  
![](images/492c998dfcc07ea0d41a0aa38cfcf2233c28092bf70f8a597ad580dbc1ccc746.jpg)

## <Screenshot>

SC040: Create or edit account
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Header</td><td rowspan=1 colspan=1>CREATE ACCOUNT</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>User Profile</td><td rowspan=1 colspan=1>Avatar, username, role (Cinema Manager or Admin)</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Side bar</td><td rowspan=1 colspan=1>Navbar: menu content</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>Form</td><td rowspan=1 colspan=1>Form to create account</td></tr></table>

SC041: Configuration (Zone 5)  
![](images/bf7f7347335d833f9e116b378afa8af8a30d95c9888345d2bfb0c8673abf2083.jpg)

<Screenshot>  
SC041: Configuration
<table><tr><td>#</td><td>Component</td><td>Description</td></tr><tr><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">User Profile</td><td colspan="1" rowspan="1">Avatar, username, role (Cinema Manager or Admin)</td></tr><tr><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">Side bar</td><td colspan="1" rowspan="1">Navbar: menu content</td></tr><tr><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">Holoday and CalendarPart</td><td colspan="1" rowspan="1">Set up Holiday and Calendar</td></tr><tr><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">Operational Settings</td><td colspan="1" rowspan="1">Timer, timeout retry, service fee</td></tr><tr><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">API Keys</td><td colspan="1" rowspan="1">API Keys of third-party API</td></tr><tr><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">Action button</td><td colspan="1" rowspan="1">“Save All Settings” button</td></tr></table>

SC042: Audit Log (Zone 5)
<table><tr><td>CINESTAR SYSTEM ADMIN 品 Dashboard</td><td>SC-A04·UC-34,UC-35 AUDIT LOG</td><td></td><td></td></tr><tr><td>山 Reports</td><td colspan="3">All users All actions 21/06/2026 V V</td></tr><tr><td>Accounts O+ Create / edit account</td><td colspan="3">21/06/2026 口 Export CSV</td></tr><tr><td>Timestamp 章 System settings 曲 Audit log 21/06 09:32</td><td>User Role Action</td><td>Entity Detail</td><td>IP</td></tr><tr><td>khoatran92 System Admin</td><td>doankhoi Admin UPDATE 21/06 09:28</td><td>User #234</td><td>Unlocked 192.168.1.12 account</td></tr><tr><td></td><td>phamquynh Manager CREATE doankhoi</td><td>Showtime #SH-4421 Expired</td><td>Avatar — IMAX 192.168.1.45 01—22:30</td></tr><tr><td>21/06 09:14</td><td>Admin DELETE</td><td>Voucher SUMMER25 cleanup</td><td>campaign 192.168.1.12</td></tr><tr><td>21/06 08:50 trantb 21/06 08:32 doankhoi Admin</td><td>UPDATE Cashier</td><td>Booking #CIN-A7X9 System</td><td>Cancelled partial 10.0.4.18 — 1 seat Service fee</td></tr><tr><td>21/06 08:01 phamquynh Manager CREATE</td><td>UPDATE Settings Movie #M-118</td><td>5000 → 6000 Imported from</td><td>Edit withLovable × TMDB: Dune 192.168.1.45</td></tr><tr><td colspan="4">Part Two Readonly·immutable·retention 365 days.</td></tr></table>

## <Screenshot>

SC042: Audit Log
<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Component</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>User Profile</td><td rowspan=1 colspan=1>Avatar, username, role (Cinema Manager or Admin)</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Side bar</td><td rowspan=1 colspan=1>Navbar: menu content</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Filter box</td><td rowspan=1 colspan=1>Admin can filter for easily finding the wanted logs, include button “Export CSV”</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>Audit Log Box</td><td rowspan=1 colspan=1>Include information like: Timestamp (date with hour detail), Username, role, action,entity, detail, IP</td></tr><tr><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Header</td><td rowspan=1 colspan=1>AUDIT LOG</td></tr></table>

## 5. Non-Functional Requirements

This section describes the operation of the system with respect to the Use Case Specifications section (Functional requirements). This comprises mostly of the technical architecture of the system which could be referred to as the quality of the system.

Performance Requirements (Core)
<table><tr><td rowspan=1 colspan=1>Title</td><td rowspan=1 colspan=1>Variables / Criteria</td><td rowspan=1 colspan=1>Remarks</td></tr><tr><td rowspan=1 colspan=1>Response</td><td rowspan=1 colspan=1>Time - Measurement Point: Page</td><td rowspan=1 colspan=1>- Homepage, Movie List, and Movie Detail pages shall load</td></tr></table>

Prepared By A Nguyen

<table><tr><td rowspan=1 colspan=1>Time</td><td rowspan=1 colspan=1>load (Homepage/Movie List/MovieDetail), Seat map update, Seat-selection conflict response, Searchautocomplete, Payment initiation,Refund calculation, Age-eligibilityCheck- Statistic Type: 95th percentile- Measurement Period: Per request,under normal &amp; peak loadPlatform: Customer Web, CashierPOS- Error Rate: &lt; 0.1% failedrequests</td><td rowspan=1 colspan=1>within 2 seconds for 95% of requests under normal load.- Seat status changes (LOCK/RELEASE/SOLD) shall be reflected toall connected clients within 100ms per CBR-03.When two users select the same seat simultaneously, the losingrequest shall receive a &quot;seat unavailable&quot; notification within500ms (CBR-03).- Search autocomplete (UC08) shall return suggestions within500ms, debounced 300ms client-side.- The refund-eligibility calculation (CBR-05) shall execute inunder 100ms, computed in seconds (not rounded) to avoiddisputes at the 1-hour/3-hour boundaries.- The online age-eligibility check (CBR-04, T13/T16/T18) shallexecute in under 200ms as part of UC09/UC16, prior to seat-lockconfirmation.- The system shall process at least 50 concurrent seat-lock-to-payment transactions/minute per cinema location during peakload (e.g., premiere weekend).</td></tr><tr><td rowspan=1 colspan=1>Workload</td><td rowspan=1 colspan=1>- Workload percentage at peaktime.- Workload percentage at off-peaktime.</td><td rowspan=1 colspan=1>- At peak load (weekend evenings, premiere days), CPU usageshall not exceed 70%, reserving headroom for background jobs(showtime-freeze checks per CBR-09, scheduled SMS/emailreminders).- At off-peak time, CPU usage shall remain below 30%.</td></tr><tr><td rowspan=1 colspan=1>Scalability</td><td rowspan=1 colspan=1>Ease of Scalability.</td><td rowspan=1 colspan=1>- The architecture shall support horizontal scaling (addingapplication server instances) to handle increased load duringpremieres/holidays without redesigning the booking and seat-locking modules.- The system shall support adding new cinema locations,screening rooms, and showtimes without schema orarchitecture changes.</td></tr><tr><td rowspan=1 colspan=1>Platform</td><td rowspan=1 colspan=1>Hardware.Software.External System Integration.</td><td rowspan=1 colspan=1>- Browsers: latest 2 versions of Chrome, Edge, Safari, Firefox.- Devices: Mobile, Tablet, Desktop — responsive web forCustomer; POS on Desktop/Tablet with thermal printer &amp;card terminal for Cashier.- OS (back-office/admin): Windows (latest + 2 previousversions), macOS (latest + 2 previous versions).- External Systems: Payment Gateways — VNPay, MoMo,VISA/Mastercard (CBR-06, UC13); Email Service (CBR-15,UC14); TMDB API (UC27).</td></tr></table>

## Availability (Core)

<table><tr><td colspan="1" rowspan="1">Title</td><td colspan="1" rowspan="1">Variables / Criteria</td><td colspan="1" rowspan="1">Remarks</td></tr><tr><td colspan="1" rowspan="1">Availability</td><td colspan="1" rowspan="1">- Percentage of time available- Measurement Period: Monthly- Scope: Booking &amp; Paymentfunctions (critical path)</td><td colspan="1" rowspan="1">- The system shall be available 99.5% of the time on a monthlybasis, excluding scheduled maintenance windows.- Critical functions (seat booking, payment processing, seat-locktimers) shall have priority over non-critical functions (e.g.,reporting dashboard) during partial outages.</td></tr><tr><td colspan="1" rowspan="1">Backup</td><td colspan="1" rowspan="1">- Backup frequency- Backup retention- Restore testing frequency</td><td colspan="1" rowspan="1">- Full database backup shall be triggered daily at 02:00 AM, withincremental backups every 6 hours.- Backups shall be retained for at least 30 days in a separatestorage location/region from production.- Backup restoration shall be tested quarterly to verify dataintegrity.</td></tr><tr><td colspan="1" rowspan="1">Recovery(MTTR)</td><td colspan="1" rowspan="1">- Recovery Time Objective (RTO)- Recovery Point Objective (RPO)- In-progress transaction handling</td><td colspan="1" rowspan="1">- Critical functions (booking, seat-lock, payment) shall recoverwithin 30 minutes of a failure (RTO).- Data loss in the event of a failure shall not exceed 15 minutesof transaction data (RPO) — aligned with the CBR-06 payment</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">window, since bookings stuck in PENDING_PAYMENT within thisrange auto-expire on their own.- Bookings left in PENDING_PAYMENT status during an outageshall automatically transition to EXPIRED and release held seatsupon system recovery (CBR-06).</td></tr><tr><td colspan="1" rowspan="1">TimeSynchronization</td><td colspan="1" rowspan="1">- Clock drift tolerance across servers- Dependent business rules</td><td colspan="1" rowspan="1">- All application and database servers shall be synchronized viaNTP with drift not exceeding 100ms, since Showtime Freeze(CBR-09) and Refund Policy (CBR-05) both depend on a single,consistent server NOW() value.</td></tr><tr><td colspan="1" rowspan="1">Failover /Redundancy</td><td colspan="1" rowspan="1">- Payment gateway redundancy- Seat-lock session store resilience</td><td colspan="1" rowspan="1">- If one payment gateway (VNPay/MoMo/VISA) is unavailable,the system shall present remaining payment options withoutblocking checkout (UC13).- Active seat locks (CBR-01) shall be stored in a fault-tolerantcache (e.g., Redis); the cache shall support immediate bulktermination of all active sessions in a room set toMAINTENANCE, releasing locked seats (CBR-16).</td></tr></table>

## Security Requirements (Core)

<table><tr><td rowspan=1 colspan=1>Title</td><td rowspan=1 colspan=1>Variables / Criteria</td><td rowspan=1 colspan=1>Remarks</td></tr><tr><td rowspan=1 colspan=1>Authentication</td><td rowspan=1 colspan=1>- All users must authenticatebefore accessing any protectedresource. The system supports twologin methods: Email + Password (allroles) and Google OAuth (Customeronly).</td><td rowspan=1 colspan=1>- Applies to UC-02 (Login). Staff roles (Cashier, CinemaManager, System Admin, Concession Staff) must use Email+ Password only — Google OAuth is disabled for theseroles.</td></tr><tr><td rowspan=1 colspan=1>JWT TokenManagement</td><td rowspan=1 colspan=1>- Upon successful login, the systemissues a signed JWT access token.The token must: (a) be signed withHS256 or RS256; (b) expire within adefined period (recommended: 60minutes); (c) be invalidatedimmediately on logout orpassword change.</td><td rowspan=1 colspan=1>- Applies to UC-02, UC-03, UC-04, UC-05. When a passwordis changed/reset, all active tokens for that account acrossall devices must be revoked (see UC-05 AF1, UC-04 MainFlow step 15).</td></tr><tr><td rowspan=1 colspan=1>Account Lockout</td><td rowspan=1 colspan=1>- After 5 consecutive failed loginattempts, the account isautomatically locked for 15minutes. During lockout, all loginattempts are rejected regardless ofwhether the password is correct.</td><td rowspan=1 colspan=1>- Applies to UC-02 (EF2). After lockout expires, the failedattempt counter resets. System Admin can manually unlockaccounts (UC-35).</td></tr><tr><td rowspan=1 colspan=1>OTP Security</td><td rowspan=1 colspan=1>- All OTP codes must: (a) be exactly6 digits; (b) expire after 5 minutes;(c) be invalidated after 3 incorrectattempts; (d) support resend aftera 60-second cooldown; (e) only bevalid for the specific action theywere issued for (registration,password reset).</td><td rowspan=1 colspan=1>Applies to CBR-15, UC-01, UC-04. OTPs must be storedtemporarily in server-side cache (not in the database) andcleared immediately after use or expiry.</td></tr><tr><td rowspan=1 colspan=1>Role-Based AccessControl (RBAC)</td><td rowspan=1 colspan=1>- The system enforces RBAC for allendpoints and UI pages. Each APIendpoint must verify both: (a) thatthe user is authenticated (validJWT); and (b) that the user&#x27;s rolehas permission for the requestedaction. Unauthorized requestsreceive HTTP 403.</td><td rowspan=1 colspan=1>- Defined roles: Customer, Cashier, Cinema Manager,System Admin, Concession Staff. Permission matrix isdefined in Section 2.5. Any attempt to access apage/function outside the user&#x27;s permitted role must beblocked server-side — client-side hiding alone is notsufficient.</td></tr><tr><td rowspan=1 colspan=1>HTTPS / TransportSecurity</td><td rowspan=1 colspan=1>- All communication betweenclient and server must use HTTPS(TLS 1.2 or higher). HTTPconnections must be automatically</td><td rowspan=1 colspan=1>- Applies to all users, all endpoints, including paymentcallbacks from VNPay, MoMo (CBR-06, UC-13). All API keysfor external services (TMDB, SendGrid, Twilio, VNPay,MoMo) must be transmitted over HTTPS only.</td></tr></table>

![](images/29453ba917d82a54df5dc564d86654fd7307d2789453bf15564110f0aa48c4e6.jpg)

<table><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>redirected to HTTPS. Self-signedcertificates are not allowed inproduction.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Input Validation &amp;InjectionPrevention</td><td rowspan=1 colspan=1>All user inputs must be validatedand sanitized on the server side.The system must be protectedagainst: (a) SQL Injection — useparameterized queries or ORM; (b)XSS (Cross-Site Scripting) —escape all output rendered inHTML; (c) CSRF (Cross-SiteRequest Forgery) — use CSRFtokens for all state-changingrequests.</td><td rowspan=1 colspan=1>- Applies to all form submissions (registration, booking,review, admin forms). Client-side validation improves UXbut is not a substitute for server-side validation. =&gt; Server-side validation required.</td></tr><tr><td rowspan=1 colspan=1>SessionTermination</td><td rowspan=1 colspan=1>The system must provide a&quot;Logout&quot; function available on allpages once authenticated. Logoutmust: (a) invalidate the JWTserver-side; (b) clear allauthentication cookies from thebrowser. After logout, usingthe browser Back button must notrestore access to protected pages.</td><td rowspan=1 colspan=1>Applies to UC-03.</td></tr><tr><td rowspan=1 colspan=1>API Key &amp; SecretManagement</td><td rowspan=1 colspan=1>- All third-party API keys andsecrets (TMDB, SendGrid, Twilio,VNPay, MoMo) must be stored inenvironment variables or a secretsmanager — never hardcoded insource code or committed toversion control.</td><td rowspan=1 colspan=1>-Keys must be rotatable without requiring code changes. Ifa key is compromised, the system must allow immediatereplacement without downtime.</td></tr></table>

## 6. Other Requirements

Common field controls

6.1.1 General Rules

## 6.1.2 Specific Field Specifications

Besides the common controls defined in Section 6.1.1, the following important fields have specific validation rules and behaviors applied across the system:

<table><tr><td colspan="1" rowspan="1">#</td><td colspan="1" rowspan="1">Field Name</td><td colspan="1" rowspan="1">Control Type</td><td colspan="1" rowspan="1">Properties &amp; ValidationRules</td><td colspan="1" rowspan="1">Notes / Usage</td></tr><tr><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">Original Title</td><td colspan="1" rowspan="1">Free Text (SingleLine)</td><td colspan="1" rowspan="1">- Optional- 5 – 150 characters</td><td colspan="1" rowspan="1">- Used for TMDB importand internal referenceor input manually</td></tr><tr><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">Voucher Code</td><td colspan="1" rowspan="1">Free Text (Single Line</td><td colspan="1" rowspan="1">- Required - 8 – 20characters- Alphanumeric +hyphen only- Auto convert toUPPERCASE- Must be unique</td><td colspan="1" rowspan="1">- Tier 3 vouchers</td></tr><tr><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">Room Name</td><td colspan="1" rowspan="1">Free Text (Single Line</td><td colspan="1" rowspan="1">- Required - 3 – 50characters- Unique within the</td><td colspan="1" rowspan="1">- E.g. "IMAX 01”, “VIPHall 2"</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">cinema</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">Room Type</td><td colspan="1" rowspan="1">：Single ChoiceDropdown</td><td colspan="1" rowspan="1">- Required- Values: 2D, 3D, IMAX,4DX, Dolby Atmos,Standard</td><td colspan="1" rowspan="1">- Affects surcharge &amp;pricing</td></tr><tr><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">Email</td><td colspan="1" rowspan="1">Free Text (SingleLine)</td><td colspan="1" rowspan="1">- Required- Valid email format- Maximum 100characters- Unique in system</td><td colspan="1" rowspan="1">- Registration, Login,Notifications</td></tr><tr><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">Phone Number</td><td colspan="1" rowspan="1"> Free Text (SingleLine)</td><td colspan="1" rowspan="1">- Vietnamese format (10or 11 digits)- Starts with 0 or +84</td><td colspan="1" rowspan="1">- Customer profile, SMS</td></tr><tr><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">Password</td><td colspan="1" rowspan="1">必Free Text (SingleLine)</td><td colspan="1" rowspan="1">- Minimum 8 characters- At least 1 letter + 1Number- Strengthindicator</td><td colspan="1" rowspan="1">- Registration &amp; ResetPassword</td></tr><tr><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">必Date &amp; Time</td><td colspan="1" rowspan="1">Date and Time</td><td colspan="1" rowspan="1">- 24-hour format- Prevent past dates fornew Showtime</td><td colspan="1" rowspan="1">- Showtime, Campaignperiod</td></tr><tr><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">小Description</td><td colspan="1" rowspan="1">Text Area</td><td colspan="1" rowspan="1">- Maximum 2000characters</td><td colspan="1" rowspan="1">- Movie description,Promotion description</td></tr><tr><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">Review of Customer</td><td colspan="1" rowspan="1">Text Area</td><td colspan="1" rowspan="1">- About 65000+characters</td><td colspan="1" rowspan="1">- Customer's review</td></tr></table>

Common Messages Configuration
<table><tr><td>Message Type</td><td>Remarks</td></tr><tr><td>In-line Error Message</td><td>Display in red italic text. Display below error field.</td></tr><tr><td>必</td><td>Highlight error field in red.</td></tr><tr><td></td><td>Message is displayed when there is error in validation.</td></tr><tr><td>In-field Error Message </td><td>Display in red italic text.</td></tr><tr><td></td><td>Display inside error field, completely cover the content of the field.</td></tr><tr><td></td><td></td></tr><tr><td>小 </td><td>Upon selecting the field, the message disappears and the content is displayed again.</td></tr><tr><td></td><td>Highlight error field in red.</td></tr><tr><td></td><td>Message is displayed when there is error in validation.</td></tr><tr><td></td><td>Sample:</td></tr><tr><td></td><td>Description text Wrong entry / Entry required</td></tr><tr><td></td><td>Y Y Where Description Text is the placeholder.</td></tr><tr><td></td><td>V “Wrong entry / Entry required” is the message content.</td></tr><tr><td>Error Message</td><td>Pop-Up contains only message content and a button “Close&quot;.</td></tr><tr><td></td><td>Clicking outside of the pop-up does not close it, only button “Close&quot; on the pop-up does.</td></tr><tr><td></td><td></td></tr><tr><td></td><td>After closing popup, return to the current screen.</td></tr><tr><td></td><td>Message is displayed when there is error in validation.</td></tr><tr><td>Confirmation Message</td><td>Pop-Up contains only message content and two buttons “Yes&quot;, “No”.</td></tr><tr><td></td><td>Clicking outside of the pop-up does not close it, only button “Yes&quot; or “No&quot; does.</td></tr><tr><td></td><td>After closing popup, performs the corresponding function or action, which is described</td></tr><tr><td></td><td>specifically in each place using the Pop-up Confirmation Message.</td></tr><tr><td></td><td>Message is displayed when there needs a confirmation of action.</td></tr><tr><td>Informing Message</td><td>Pop-Up contains only message content and will disappear after 10s.</td></tr><tr><td></td><td>Message is displayed after the system successfully performs a certain function or action.</td></tr><tr><td>Standard platform</td><td>Any standard platform message can be presented here.</td></tr><tr><td>Message</td><td></td></tr></table>

## View Columns Display

Unless otherwise stated, view columns’ display specifications are:

Displayed color & fonts are as specified in approved screen designs.

 When the text to be displayed is longer than the width of cell, cut the text at the end of first line, and replace the missing characters with “…”. Hovering mouse over this “…” will pop up a tooltip at mouse position that displays full content of the respective cell.

Unless otherwise stated, view columns’ headers are:

 Is unsorted by default.

 When unsorted, show icon as follows:

PIMS CATEGORY NAME

 When sorted in ascending, show icon as follows:

When sorted in descending, show icon as follows:

## Pagination

Unless stated otherwise, pagination-related behavior in all views of the system will follow the following specifications:

 When user performs a new search (both completely new and searching within the current search results), refresh table, go back to page 1.

 When user changes the pagination setting (number of items to show per page), refresh table, go back to page 1.

 When user is in page 1, disable buttons of “<<” and “<”

 When user is in the last page, disable buttons of “>>” and “>”

 Otherwise, enable all buttons.

 Button “<” and “>” move the pagination backward or forward by 1.

Button “<<” or “>>” move the pagination to page 1 or the last page.

If there is 1 page, still display the pagination with 1 page.

 On the most left position, the system displays all records found that satisfied the current condition (display all or searched or filtered, etc…).

 User can input the number of pagination they want to go to, next to the total number of pagination.

182 items Sample:

 Default page size: 10 items per page. User may change to 20 or 50 items per page via the page size selector.

## Search Component

Unless stated otherwise, search-related behavior in all views of the system will follow the following specifications:

 Search field is a Free Text (single line of text) field, thus it follows this field’s common properties.

 Search behavior follows “contain” logic, where the system searches all presenting columns for records that have value containing the keyed in value.

 Searched results are presented by refreshing the table listing information and the system updates pagination information accordingly.

 If keyed in value is blank, the system will reset to the default view information.

 Search is case-insensitive, supports basic Vietnamese diacritic removal, and triggers after 500ms of inactivity.

## Bulk Action

Unless stated otherwise, Bulk Action behavior in all views of the system will follow the following specifications:

 In the table listing, the first column will always be a checkbox columns allowing user to select records/items to apply Bulk Action.

 Selecting the checkbox on Column Header will select all checkboxes only on the current pagination of the table listing.

 Upon jumping between pagination, the selected state of checkboxes is kept.

 Users can select Bulk Action from the Dropdown list or available bulk action buttons (depending on the system) to apply to the selected items.

 For Dropdown list Bulk Action:

 Bulk Action is the default option, which performs nothing when apply.

 Value list contains:

 Bulk Action.

 Export.

Delete.

 For available bulk action buttons:

 These buttons are enable only when at least 1 checkbox is selected.

 Button includes:

Delete.

 Export.

Note Scope: Bulk Action is applicable to administrative and management views only (UC33 — Moderate Reviews, UC34 — Manage User Accounts). It is not available on customer-facing screens.

## 7. Integration

## 7.1: Payment Gateway

<table><tr><td>Providers</td><td>VNPay, MoMo, VISA / Mastercard</td></tr><tr><td>Used In</td><td>UC-13 (Process Online Payment), UC-23 (Process Refund)</td></tr><tr><td>Direction</td><td>Bidirectional</td></tr><tr><td>Reference</td><td>VNPay Merchant Technical Document; MoMo eWallet API Documentation</td></tr><tr><td rowspan="4">Data Sent to Gateway</td><td>Booking ID, total amount, currency (VND)</td></tr><tr><td>• Selected payment method</td></tr><tr><td>• Redirect URL (success / fail callback)</td></tr><tr><td>• Payment callback: status (SUCCESS / FAIL / TIMEOUT), transaction ID, gateway</td></tr><tr><td>Data Received from Gateway</td><td>reference, timestamp</td></tr><tr><td>Authentication</td><td>• Refund callback: refund status, refund ID API key + HMAC-SHA256 signature per request. All callbacks verified against</td></tr><tr><td>Error Handling</td><td>gateway signature before updating booking status.</td></tr><tr><td rowspan="2"></td><td>FAIL callback  Booking = FAILED; seats released (CBR-06)</td></tr><tr><td>No callback within 15 minutes → Booking = EXPIRED; seats released (CBR-06) Refund callback failure → logged for manual follow-up; booking status</td></tr></table>

7.2: Email Service
<table><tr><td rowspan=1 colspan=1>Provider</td><td rowspan=1 colspan=1>SendGrid</td></tr><tr><td rowspan=1 colspan=1>Used In</td><td rowspan=1 colspan=1>UC-01 (OTP), UC-04 (OTP + reset link), UC-14 (booking confirmation), UC-23 (refundconfirmation), UC-31 (campaign emails)</td></tr><tr><td rowspan=1 colspan=1>Direction</td><td rowspan=1 colspan=1>Outbound only (System → SendGrid → Customer)</td></tr><tr><td rowspan=1 colspan=1>Reference</td><td rowspan=1 colspan=1>SendGrid Email API Guide — https://docs.sendgrid.com/</td></tr><tr><td rowspan=1 colspan=1>Data Sent to EmailService</td><td rowspan=1 colspan=1>Recipient email address, subject, email body (HTML)Dynamic fields: booking code, QR code attachment, OTP, refund amount</td></tr><tr><td rowspan=1 colspan=1>Data Received fromEmail Service</td><td rowspan=1 colspan=1>Delivery status webhook (optional — logged but not required for bookingvalidity)</td></tr><tr><td rowspan=1 colspan=1>Authentication</td><td rowspan=1 colspan=1>SendGrid API key stored in environment variables (never hardcoded per SecurityRequirement 5.3).</td></tr><tr><td rowspan=1 colspan=1>Error Handling</td><td rowspan=1 colspan=1>OTP email fails → System does not create account; Guest shown error (UC-01EF6)Booking confirmation email fails → Retry up to 3 times with exponentialbackoff; failure logged; booking remains CONFIRMED; QR accessible via UC-15(UC-14 EF1)Campaign email fails → Logged; no retry; does not affect campaign record</td></tr></table>

7.3: SMS Service (Twilio)
<table><tr><td colspan="1" rowspan="1">Provider</td><td colspan="1" rowspan="1">Twilio</td></tr><tr><td colspan="1" rowspan="1">Used In</td><td colspan="1" rowspan="1">UC-14 (SMS booking confirmation), UC-38 (Automated Showtime Reminder)</td></tr><tr><td colspan="1" rowspan="1">Direction</td><td colspan="1" rowspan="1">Outbound only (System → Twilio → Customer)</td></tr><tr><td>Reference</td><td>Twilio SMS API Documentation — https://www.twilio.com/docs/sms</td></tr><tr><td>Data Sent to SMS</td><td>• Recipient phone number</td></tr><tr><td>Service</td><td>Message body: movie name, showtime date/time, booking code</td></tr><tr><td></td><td>• Scheduled send time (for UC-38 reminder)</td></tr><tr><td>Data Received from</td><td>• Delivery status webhook (optional — logged only)</td></tr><tr><td>SMS Service</td><td></td></tr><tr><td>Authentication</td><td>Twilio Account SID + Auth Token stored in environment variables.</td></tr><tr><td>Error Handling</td><td>• SMS delivery fails → Failure logged; no retry</td></tr><tr><td></td><td>• Booking validity is not affected — SMS is a supplementary channel</td></tr><tr><td></td><td>• Customer can access all booking details via UC-15 (UC-14 EF2)</td></tr></table>

7.4: Movie Content Provider
<table><tr><td rowspan=1 colspan=1>Provider</td><td rowspan=1 colspan=1>The Movie Database (TMDB)</td></tr><tr><td rowspan=1 colspan=1>Used In</td><td rowspan=1 colspan=1>UC-27 (Import Movie from TMDB)</td></tr><tr><td rowspan=1 colspan=1>Direction</td><td rowspan=1 colspan=1>Bidirectional</td></tr><tr><td rowspan=1 colspan=1>Reference</td><td rowspan=1 colspan=1>TMDB API Documentation —https://developer.themoviedb.org/reference/intro/getting-started</td></tr><tr><td rowspan=1 colspan=1>Data Sent to TMDB</td><td rowspan=1 colspan=1>Search query: movie title keyword or TMDB ID</td></tr><tr><td rowspan=1 colspan=1>Data Received fromTMDB</td><td rowspan=1 colspan=1>Title (original + Vietnamese), synopsis, release date, runtime• Poster URL, trailer URL, genre list, cast, director, TMDB rating</td></tr><tr><td rowspan=1 colspan=1>Authentication</td><td rowspan=1 colspan=1>TMDB API key stored in environment variables. Read-only access — no writeoperations performed on TMDB.</td></tr><tr><td rowspan=1 colspan=1>Error Handling</td><td rowspan=1 colspan=1>TMDB unavailable during UC-27  Cinema Manager shown error; manualentry remains available (UC-27 EF)TMDB unavailable during UC-07 → System displays locally stored metadataonly; no disruption to page (UC-07 EF3)</td></tr></table>

7.5: Google OAuth Service
<table><tr><td rowspan=1 colspan=1>Provider</td><td rowspan=1 colspan=1>Google Identity Platform</td></tr><tr><td rowspan=1 colspan=1>Used In</td><td rowspan=1 colspan=1>UC-02 (Login — Customer only)</td></tr><tr><td rowspan=1 colspan=1>Direction</td><td rowspan=1 colspan=1>Bidirectional</td></tr><tr><td rowspan=1 colspan=1>Reference</td><td rowspan=1 colspan=1>Google Identity — https://developers.google.com/identity</td></tr><tr><td rowspan=1 colspan=1>Data Sent to Google</td><td rowspan=1 colspan=1>• OAuth authorisation request: client ID, redirect URI, scope (email, profile)</td></tr><tr><td rowspan=1 colspan=1>Data Received fromGoogle</td><td rowspan=1 colspan=1>• ID token, access token• User profile: display name, email address, avatar URL, Google ID</td></tr><tr><td rowspan=1 colspan=1>Authentication</td><td rowspan=1 colspan=1>OAuth 2.0 Authorization Code Flow. Client ID and Client Secret stored inenvironment variables.</td></tr><tr><td rowspan=1 colspan=1>Scope Restriction</td><td rowspan=1 colspan=1>Google OAuth is available to Customer role only. Staff roles (Cashier, CinemaManager, System Admin, Concession Staff) must use email/password loginexclusively.</td></tr><tr><td rowspan=1 colspan=1>Error Handling</td><td rowspan=1 colspan=1>• Google OAuth unavailable  Email/password login remains available asfallback; Google Sign-In button disabled with notice (UC-02 EF)• Token validation fails  Login rejected; Actor prompted to retry or useemail/password</td></tr></table>

7.6: AI Support
<table><tr><td>Provider</td><td>External Al conversational service (TBD)</td></tr><tr><td>Used In</td><td>UC-38 (Chat with AI Support)</td></tr><tr><td>Direction</td><td>Bidirectional</td></tr><tr><td>Reference</td><td>To be defined based on selected Al provider</td></tr><tr><td>Data Sent to Al Support</td><td>Customer query / chat message</td></tr><tr><td rowspan="3"></td><td>Customer profile context: booking history, preferences</td></tr><tr><td>Current movie catalogue: titles, genres, showtimes, ratings</td></tr><tr><td>• Active session context</td></tr><tr><td>Data Received from Al</td><td>• Al-generated response: FAQ answer, movie recommendation</td></tr><tr><td>Support</td><td>• Showtime suggestion, booking guidance path</td></tr><tr><td>Authentication</td><td>API key / Bearer token stored in environment variables.</td></tr><tr><td>Error Handling</td><td>• Al Service unavailable → Chat widget displays: &#x27;Al Support is temporarily unavailable. Please contact our staff for assistance.&#x27;</td></tr></table>

## 7.7: Identity Verification Service

<table><tr><td>Provider</td><td>External eKYC service (e.g. VNPay eKYC / FPT.AI / ViettelPay ID — TBD)</td></tr><tr><td>Used In</td><td>UC-40 (Identity Verification)</td></tr><tr><td>Direction</td><td>Bidirectional</td></tr><tr><td>Reference</td><td>To be defined based on selected eKYC provider</td></tr><tr><td>Data Sent to Al Support</td><td>• CCCD/CMND front photo • CCCD/CMND back photo • Selfie photo</td></tr><tr><td>Data Received from Al</td><td>Document authenticity result (genuine / fake / blurred)</td></tr><tr><td>Support</td><td>• OCR-extracted data: CCCD number, full name, date of birth • Face-match result: score (Decimal) + pass/fail against faceMatchThreshold (0.85)</td></tr><tr><td>Authentication</td><td>API key / Bearer token stored in environment variables</td></tr><tr><td>Error Handling</td><td>• Identity Verification Service unavailable or timeout → System displays: &quot;Dch v</td></tr><tr><td></td><td>xác thc tm thi không kh dng. Vui lòng th i sau.&quot;No profile changes are saved.</td></tr><tr><td></td><td>• Document validation fails (fake ID / blurred image) → identityVerificationStatus = REJECTED, error reason logged, customer shown a re-upload prompt.</td></tr><tr><td></td><td></td></tr><tr><td></td><td>• Face-match fails (selfie does not match document) → identityVerificationStatus =</td></tr><tr><td></td><td>REJECTED, customer shown a re-upload prompt.</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>• Core booking functions (UC09, UC16) are not affected — identity verification is</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>optional and only feeds into age-restriction confidence (CBR-04), not a hard booking</td></tr></table>

## 7.8: Summary

The table below provides a quick reference of all external integrations in the Cinema Management System.

<table><tr><td colspan="1" rowspan="1">#</td><td colspan="1" rowspan="1">External System</td><td colspan="1" rowspan="1">Provider</td><td colspan="1" rowspan="1">Direction</td><td colspan="1" rowspan="1">Used In</td></tr><tr><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">Payment Gateway</td><td colspan="1" rowspan="1">VNPay / MoMo /VISA</td><td colspan="1" rowspan="1">Bidirectional</td><td colspan="1" rowspan="1">UC-13, UC-23</td></tr><tr><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">Email Service</td><td colspan="1" rowspan="1">SendGrid</td><td colspan="1" rowspan="1">Outbound only</td><td colspan="1" rowspan="1">UC-01, UC-04, UC-14, UC-23, UC-31</td></tr><tr><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">SMS Service</td><td colspan="1" rowspan="1">Twilio</td><td colspan="1" rowspan="1">Outbound only</td><td colspan="1" rowspan="1">UC-14, UC-39</td></tr><tr><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">Movie Content</td><td colspan="1" rowspan="1">TMDB</td><td colspan="1" rowspan="1">Bidirectional</td><td colspan="1" rowspan="1">UC-27</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Provider</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">Google OAuth Service</td><td colspan="1" rowspan="1">Google</td><td colspan="1" rowspan="1">Bidirectional</td><td colspan="1" rowspan="1">UC-02</td></tr><tr><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">Al Support</td><td colspan="1" rowspan="1">TBD</td><td colspan="1" rowspan="1">Bidirectional</td><td colspan="1" rowspan="1">UC-38</td></tr><tr><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">Identity VerificationService</td><td colspan="1" rowspan="1">VNPay eKYC /ViettelPay ID/ FPT.AI</td><td colspan="1" rowspan="1">Bidirectional</td><td colspan="1" rowspan="1">UC-40</td></tr></table>

## 8. AI-Powered Features

## 8.1 AI Movie Recommendation Engine

## 8.1.1 Business Problem

The current Homepage (UC06) and Movie Detail page (UC07) display identical content to all users regardless of viewing history or preferences. Customers must manually browse or search to find relevant films, resulting in increased time-todecision and missed discovery of suitable titles.

## 8.1.2 Solution Overview

A personalised recommendation engine surfaces contextually relevant movies to each logged-in Customer, automatically prioritizing and displaying these recommended titles at the very top of the page to eliminate discovery friction and maximize booking conversion. The engine powers this premium placement using a hybrid algorithm that combines two complementary approaches:

\- Collaborative Filtering — identifies users with similar booking history and surfaces films they watched that the current Customer has not. Requires a minimum data threshold to activate.

\- Content-Based Filtering — identifies films with overlapping attributes (genre, age rating, cast, director) relative to the Customer's viewing history. Activates from the first completed booking.

The hybrid approach compensates for each method's blind spot: collaborative filtering fails for new users (cold start);   
content-based filtering fails to surface genre diversity.

<table><tr><td>Involvement</td><td>Detail</td></tr><tr><td>Input signals</td><td>Booking history (genre, age rating, time slot), UC32 review ratings, UC08 search keywords, LoyaltyAccount.tier</td></tr><tr><td>Output</td><td>&quot;Recommended for You&quot; carousel on Homepage · &quot;You May Also Like&quot; section on Movie Detail page (below Reviews section)</td></tr><tr><td>Minimum data threshold</td><td>≥ 2 confirmed bookings required before personalised recommendations activate. Below threshold → popularity-ranked fallback (non-personalised)</td></tr><tr><td>Cold start handling</td><td>Genre-preference prompt shown on first login (3-tap selector: Action / Romance / Horror / Sci-Fi / etc.) stored as preferredGenres on Customer profile; used as seed for content-based filtering until booking history is established</td></tr></table>

Referenced UCs: UC06 (UI extended), UC07 (UI extended), UC08 (search keyword used as input signal), UC32 (star rating used as preference signal)

Referenced CBRs: CBR-04 — age-restricted films are filtered from recommendations before display. A Customer ineligible to book a T18 film will never see it recommended, regardless of algorithm output. Business rules take precedence over AI output.

What this feature does NOT do:

 Does not influence pricing, discount eligibility, or any CBR calculation

 Does not modify the Booking flow (UC09–UC13) in any way

 Does not share individual Customer preference data with any third party

## Acceptance Criteria:

 Recommendation section visible to all Customers with ≥ 2 confirmed bookings

 Age-restricted films never appear in recommendations for ineligible Customers (zero tolerance)

 Cold-start fallback renders within 200 ms regardless of personalisation data availability

 Click-through rate on recommended titles ≥ 15% above non-personalised browse baseline (measured over 30-day live period)

## 8.2 AI-Powered Customer Support Chatbot

## 8.2.1 Business Problem

High-frequency, low-complexity queries — showtime availability, booking status, refund policy, loyalty point balance — require either waiting for staff availability or navigating multiple screens. This creates unnecessary friction for time-sensitive decisions such as checking seat availability before committing to a booking.

## 8.2.2 Solution Overview

A conversational AI assistant embedded in the Customer-facing site handles high-frequency queries 24/7 without staff involvement. The bot operates on a four-step pipeline: Intent Classification → Entity Extraction → Data Pull → Response Generation. Queries the bot cannot handle with sufficient confidence are escalated to human staff.

Supported Intent Categories
<table><tr><td rowspan=1 colspan=1>Intent</td><td rowspan=1 colspan=1>Example query</td><td rowspan=1 colspan=1>Data source</td><td rowspan=1 colspan=1>ReferencedCBR/UC</td></tr><tr><td rowspan=1 colspan=1>Showtimeavailability         k</td><td rowspan=1 colspan=1>&quot;Phim Avengers còn sut ti nayhông?&quot;</td><td rowspan=1 colspan=1>Showtime.status, ShowtimeSeatavailability</td><td rowspan=1 colspan=1>UC06, UC28</td></tr><tr><td rowspan=1 colspan=1>Booking status</td><td rowspan=1 colspan=1>&quot;Vé ca tôi đt rồi chưa?&quot;</td><td rowspan=1 colspan=1>Booking (authenticated only)</td><td rowspan=1 colspan=1>UC15</td></tr><tr><td rowspan=1 colspan=1>Refund policyn</td><td rowspan=1 colspan=1>&quot;Hy vé trưc 2 ting đưc hoàn baohiêu?&quot;</td><td rowspan=1 colspan=1>CBR-05 static knowledge base</td><td rowspan=1 colspan=1>CBR-05</td></tr><tr><td rowspan=1 colspan=1>Loyalty balance</td><td rowspan=1 colspan=1>&quot;Tôi còn bao nhiêu đim?&quot;</td><td rowspan=1 colspan=1>LoyaltyAccount.balance (authenticatedonly)</td><td rowspan=1 colspan=1>UC24, CBR-07</td></tr><tr><td rowspan=1 colspan=1>Voucher validityk</td><td rowspan=1 colspan=1>&quot;Mã SUMMER20 còn dùng đưchông?&quot;</td><td rowspan=1 colspan=1>Voucher.status, validTo</td><td rowspan=1 colspan=1>CBR-12</td></tr><tr><td rowspan=1 colspan=1>F&amp;B pre-ordercutoff               k</td><td rowspan=1 colspan=1>&quot;Đt combo trưóc chiu đưchông?&quot;</td><td rowspan=1 colspan=1>CBR-07 cutoff rule</td><td rowspan=1 colspan=1>CBR-07</td></tr><tr><td rowspan=1 colspan=1>Age restrictionquery               k</td><td rowspan=1 colspan=1>&quot;Phim T16 tr em 14 tui xem đưchông?&quot;</td><td rowspan=1 colspan=1>CBR-04 static knowledge base</td><td rowspan=1 colspan=1>CBR-04</td></tr></table>

Referenced UCs: UC06, UC15, UC22, UC24 — read-only data access only. The chatbot never writes to, modifies, or deletes any system record under any circumstances.

Referenced CBRs: CBR-04, CBR-05, CBR-07, CBR-12. Bot responses are derived from these rules. If a CBR is updated, the chatbot knowledge base must be re-synced.

What this feature does NOT do:

 Cannot cancel a booking, process a refund, or modify any Booking, LoyaltyAccount, or User record

 Cannot access, display, or transmit payment data or CCCD/identity verification data

 Cannot make binding commitments on behalf of the cinema (pricing, policy exceptions, compensation)

 Cannot impersonate staff or respond as a named employee

 Intent recognition accuracy ≥ 85% on a validated test set of 200 representative Vietnamese-language queries

 Average response time ≤ 2 seconds from query submission to response display

 Escalation rate ≤ 20% of total sessions

 Zero instances of chatbot accessing or displaying payment data or CCCD data (verified by audit log sampling)

## 8.2.3 Session Context

\- Unauthenticated (Guest): General queries only (showtime, policy, F&B info). No account-specific data returned — session token required to verify identity before any personal data is accessed.

\- Authenticated (Customer): Full intent scope including personalised data (booking status, loyalty balance) after session token is confirmed.

## 8.2.4 Escalation Rules

The following query types are beyond the bot's scope and are routed to human staff:

 Booking disputes or payment discrepancies

 Account recovery or CCCD verification issues

 Any query the bot fails to classify with confidence ≥ 0.70 after 2 clarification attempts

Escalation channel: email (auto-populated with full chat transcript) or hotline link.

## 8.3 AI-Assisted Review Moderation

## 8.3.1 Business Problem

UC33 (Moderate Movie Reviews) currently requires Cinema Manager to manually review 100% of submitted reviews before they appear publicly. As booking volume scales, the pending queue becomes a bottleneck — delayed moderation causes the displayed average rating on UC07 to become stale, reducing its value as a decision signal for prospective customers.

## 8.3.2 Solution Overview

An AI text classifier pre-screens all incoming reviews and routes them into three lanes. Manager manual effort is concentrated exclusively on genuinely ambiguous cases; clear approvals and clear violations are handled automatically.

Three-Lane Classification
<table><tr><td rowspan=1 colspan=1>Lane</td><td rowspan=1 colspan=1>Trigger condition</td><td rowspan=1 colspan=1>System action</td><td rowspan=1 colspan=1>Manager actionrequired?</td></tr><tr><td rowspan=1 colspan=1>AUTO-APPROVE</td><td rowspan=1 colspan=1>Confidence ≥ 0.90 · no profanity · nospam·on-topic</td><td rowspan=1 colspan=1>Review.status = APPROVEDimmediately</td><td rowspan=1 colspan=1>X None</td></tr><tr><td rowspan=1 colspan=1>MANAGERREVIEW</td><td rowspan=1 colspan=1>0.70 ≤ confidence &lt; 0.90 · orambiguous content</td><td rowspan=1 colspan=1>Review enters Pending queue asnormal</td><td rowspan=1 colspan=1> Manual decision</td></tr><tr><td rowspan=1 colspan=1>AUTO-REJECT</td><td rowspan=1 colspan=1>Confidence ≥ 0.90 · clear violationdetected</td><td rowspan=1 colspan=1>Review.status =REJECTED ·reason logged</td><td rowspan=1 colspan=1>X None (visible inAuditLog)</td></tr></table>

Referenced UCs: UC32 (review submitted — triggers classification pipeline), UC33 (Pending queue now contains only MANAGER REVIEW lane items)

What this feature does NOT do:

 Does not modify the star rating (1–5 stars) — text content only is screened

 Does not permanently delete any review — all records retained in database regardless of status (soft decision, fully reversible)

 Does not apply different moderation standards based on Customer identity, loyalty tier, or booking history Acceptance Criteria:

 AUTO-APPROVE precision ≥ 95% (false approval rate < 5%)

 AUTO-REJECT precision ≥ 98% (false rejection rate < 2%) — threshold set high because incorrectly rejecting a legitimate customer review carries higher reputational cost than a borderline review entering the Manager queue

 Manager queue volume reduced by ≥ 60% compared to current 100%-manual baseline

 All auto-decisions auditable and reversible within UC33 interface

## 8.3.3 Violation Categories Detected

Profanity and offensive language

\- Spam patterns (repeated characters, URLs, copy-pasted blocks)

\- Off-topic content (text unrelated to the film or viewing experience)

\- Personal information exposure (phone numbers, email addresses)

## 8.3.4 Audit and Override

\- All AUTO-APPROVE and AUTO-REJECT decisions are logged in AuditLog with aiConfidenceScore and violationCategory fields — every decision is traceable and explainable

\- Cinema Manager can override any auto-decision at any time within the UC33 interface

\- Override rate is tracked as a system metric. If Manager override rate exceeds 10% over a 30-day period, model retraining is triggered — each Manager override functions as a labeled training data point (human-in-the-loop learning).

## 9. Appendices

## 9.1 Email Templates

Convention: <<Field>> = dynamic value substituted at send time. All templates use past tense for formal tone. Email prefix: [CineStar]

9.1.1 ET-01: Welcome Email – Account Registration Successful
<table><tr><td>Trigger</td><td>UC-01: After OTP verified and Customer account created</td></tr><tr><td>Send to</td><td>Newly registered Customer</td></tr><tr><td>CC</td><td>None</td></tr><tr><td>Subject</td><td>[Cinema Star] Welcome to Cinema Star, &lt;&lt;Full Name&gt;&gt;!</td></tr><tr><td>Body</td><td>Dear &lt;&lt;Full Name&gt;&gt;,</td></tr><tr><td></td><td>Your CineStar account has been successfully created. You are now ready to book tickets, earn loyalty points,</td></tr><tr><td></td><td>and enjoy exclusive offers.</td></tr><tr><td></td><td>Account Details:</td></tr><tr><td></td><td>Email: &lt;&lt;Email Address&gt;&gt; Membership ID: &lt;&lt;Membership ID&gt;&gt;</td></tr><tr><td></td><td>To get started, visit our website and explore movies now showing. If you did not create this account, please</td></tr><tr><td></td><td>contact our support team immediately.</td></tr><tr><td>Cinema Star</td><td>Sincerely,</td></tr><tr><td></td><td>Note: This is an auto-generated email, please do not reply.</td></tr><tr><td>Dear Mary Jane,</td><td></td></tr><tr><td>Account Details:</td><td></td></tr><tr><td>Email: maryjane2222@.gmail.com</td><td>Your CineStar account has been successfully created. You are now ready to book tickets, earn loyalty points, and enjoy exclusive offers.</td></tr><tr><td>Membership ID: CS278936 To get started, visit our website and explore movies now showing. If you did not create this account, please contact our support team immediately.</td><td></td></tr><tr><td></td><td></td></tr><tr><td>Sincerely,</td><td></td></tr><tr><td>Cinema Star</td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>Note: This is an auto-generated email, please do not reply.</td></tr><tr><td></td><td></td></tr></table>

9.1.2 ET-05: Booking Confirmation with E-Ticket (QR Code)
<table><tr><td>Trigger</td><td>UC-14: After booking status changes to CONFIRMED following successful payment (UC-13)</td></tr><tr><td>Send to</td><td>Customer who completed the booking</td></tr><tr><td>CC</td><td>None</td></tr><tr><td>Subject</td><td>[Cinema Star] Booking Confirmed – &lt;&lt;Movie Title&gt;&gt; on &lt;&lt;Showtime Date&gt;&gt;</td></tr><tr><td>Body</td><td>Dear &lt;&lt;Full Name&gt;&gt;,</td></tr><tr><td></td><td>Your booking has been confirmed. Please find your e-ticket details below. Booking Summary:</td></tr><tr><td></td><td>Booking ID: &lt;&lt;Booking ID&gt;&gt;</td></tr><tr><td></td><td></td></tr><tr><td></td><td>Movie: &lt;&lt;Movie Title&gt;&gt;</td></tr><tr><td></td><td>Date &amp; Time: &lt;&lt;Showtime Date &amp; Time&gt;&gt;</td></tr><tr><td></td><td>Cinema: &lt;&lt;Cinema Name&gt;&gt;- Room &lt;&lt;Room Name&gt;&gt;</td></tr><tr><td></td><td>Seats: &lt;&lt;Seat Numbers&gt;&gt;</td></tr><tr><td></td><td>Ticket Type: &lt;&lt;Seat Types&gt;&gt;</td></tr><tr><td></td><td>F&amp;B Order: &lt;&lt;F&amp;B Items &amp; Quantities&gt;&gt; (if applicable)</td></tr><tr><td></td><td>Payment Summary: Ticket Total: &lt;&lt;Ticket Subtotal&gt;&gt; VNĐ</td></tr><tr><td></td><td>F&amp;B Total: &lt;&lt;F&amp;B Subtotal&gt;&gt; VNĐ Discount Applied: -&lt;&lt;Discount Amount&gt;&gt; VNĐ Amount</td></tr><tr><td></td><td>Paid: &lt;&lt;Total Amount Paid&gt;&gt; VNĐ</td></tr><tr><td></td><td>Payment Method: &lt;&lt;Payment Method&gt;&gt;</td></tr><tr><td></td><td>Loyalty Points Earned: +&lt;&lt;Points Earned&gt;&gt; points Your QR Code is attached. Please present it at the cinema</td></tr><tr><td></td><td>entrance for check-in. Cancellation is available up to &lt;&lt;Cancellation Deadline&gt;&gt; (refer to our cancellation policy for details).</td></tr><tr><td></td><td></td></tr><tr><td></td><td>Sincerely,</td></tr><tr><td></td><td>Cinema Star&#x27;s Team</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>Note: This is an auto-generated email, please do not reply.</td></tr></table>

9.1.3 ET-02: OTP Verification – Registration
<table><tr><td></td><td></td></tr><tr><td>Trigger</td><td>UC-01: After Guest clicks &quot;Send OTP&quot; during registration</td></tr><tr><td>Send to</td><td>Guest (email entered in registration form)</td></tr><tr><td>CC</td><td>None</td></tr><tr><td>Subject</td><td>[Cinema Star] Your OTP Code for Account Registration</td></tr><tr><td rowspan="5">Body</td><td>Dear &lt;&lt;Full Name&gt;&gt;,</td></tr><tr><td>Your One-Time Password (OTP) for account registration is: &lt;&lt;OTP Code&gt;&gt;. This code is valid for 5 minutes.</td></tr><tr><td>Do not share this code with anyone. If you did not request this, please disregard this email.</td></tr><tr><td>Sincerely,</td></tr><tr><td></td></tr><tr><td></td><td>Cinema Star&#x27;s Team Note: This is an auto-generated email, please do not reply.</td></tr></table>

9.1.4 ET-03: OTP Verification – Password Reset
<table><tr><td>Trigger</td><td>UC-04: After Actor clicks &quot;Submit&quot; on Forgot Password page (OTP method)</td></tr><tr><td></td><td></td></tr><tr><td>Send to</td><td>Registered email of the Actor requesting reset</td></tr><tr><td>CC Subject</td><td>None</td></tr><tr><td>Body</td><td>[Cinema Star] Your OTP Code for Password Reset Dear &lt;&lt;Full Name&gt;&gt;,</td></tr><tr><td rowspan="6"></td><td>A request was received to reset the password for your Cinema Star account. Your OTP code for password</td></tr><tr><td>reset is: &lt;&lt;OTP Code&gt;&gt; This code is valid for 5 minutes. If you did not make this request, please ignore this</td></tr><tr><td>email — your password will remain unchanged.</td></tr><tr><td>Sincerely,</td></tr><tr><td>Cinema Star&#x27;s Team</td></tr><tr><td>Note: This is an auto-generated email, please do not reply.</td></tr></table>

9.1.5 ET-04: Password Reset Confirmation
<table><tr><td>Trigger</td><td>UC-04: After Actor successfully resets their password (Main Flow step 16)</td></tr><tr><td>Send to</td><td>Registered email of the Actor</td></tr><tr><td>CC</td><td>None</td></tr><tr><td>Subject</td><td>[Cinema Star] Your Password Has Been Successfully Reset</td></tr><tr><td>Body</td><td>Dear &lt;&lt;Full Name&gt;&gt;,</td></tr><tr><td></td><td>Your Cinema Star's account password was successfully reset on &lt;&lt;Date &amp; Time&gt;&gt;. All previously active</td></tr><tr><td></td><td>sessions on other devices have been signed out. If you did not perform this action, your account may have</td></tr><tr><td></td><td>been compromised. Please contact our support team immediately.</td></tr><tr><td></td><td>Sincerely,</td></tr><tr><td></td><td>Cinema Star's Team</td></tr><tr><td></td><td>Note: This is an auto-generated email, please do not reply.</td></tr></table>

Dear Mary Jane,

Your Cinema Star's account password was successfully reset on 15/06/2026. All previously active sessions on other devices have been signed out. If you did not perform this action, your account may have been compromised. Please contact our support team immediately.

Sincerely,

Cinema Star's Team

Note: This is an auto-generated email, please do not reply

9.1.6 ET-06: Booking Cancellation & Refund Initiated
<table><tr><td>Trigger</td><td>UC-23: After Customer or Cashier successfully cancels a booking and refund is initiated</td></tr><tr><td>Send to</td><td>Customer whose booking was cancelled</td></tr><tr><td>CC</td><td>None</td></tr><tr><td>Subject</td><td>[Cinema Star] Booking Cancelled – &lt;&lt;Booking ID&gt;&gt;</td></tr><tr><td>Body</td><td>Dear &lt;&lt;Full Name&gt;&gt;,</td></tr><tr><td></td><td>Your booking &lt;&lt;Booking ID&gt;&gt; for &lt;&lt;Movie Title&gt;&gt; on &lt;&lt;Showtime Date &amp; Time&gt;&gt; has been successfully cancelled.</td></tr><tr><td></td><td>Refund Details: Refund Amount: &lt;&lt;Refund Amount&gt;&gt; VNĐ</td></tr><tr><td></td><td>Refund Method: &lt;&lt;Original Payment Method&gt;&gt;</td></tr><tr><td></td><td>Estimated Processing Time: 3-7 business days (depending on your bank or e-wallet) Loyalty points earned</td></tr><tr><td></td><td>from this booking,</td></tr><tr><td></td><td>if any, have been reversed from your account. If you have any questions, please contact our support team with your Booking ID.</td></tr><tr><td></td><td></td></tr><tr><td></td><td>Sincerely, Cinema Star&#x27;s Team</td></tr><tr><td></td><td></td></tr><tr><td></td><td>Note: This is an auto-generated email, please do not reply.</td></tr></table>

Dear Mary Jane,

Your booking CS-987654321 for Furiosa: A Mad Max Saga on June 20, 2026 – 19:30 has been successfully cancelled.

• Refund Amount: 245,000 VND

• Refund Method: MoMo E-wallet

• Estimated ProcessingTime: 3-7 business days (depending on your bank or e-wallet)

Loyalty points earned from this booking, if any, have been reversed from your account.

If you have any questions, please contact our support team with your BookingID.

Sincerely,

Cinema Star's Team

Note: This is an auto-generated email, please do not reply.

9.1.7 ET-07: Account Temporarily Locked
<table><tr><td colspan="1" rowspan="1">Trigger</td><td colspan="1" rowspan="1">UC-02 (EF2): After 5 consecutive failed login attempts cause account lockout</td></tr><tr><td colspan="1" rowspan="1">Send to</td><td colspan="1" rowspan="1">Registered email of the affected account</td></tr><tr><td colspan="1" rowspan="1">CC</td><td colspan="1" rowspan="1">None</td></tr><tr><td>Subject</td><td>[Cinema Star] Security Alert – Your Account Has Been Temporarily Locked</td></tr><tr><td>Body</td><td>Dear &lt;&lt;Full Name&gt;&gt;,</td></tr><tr><td></td><td>We detected 5 consecutive failed login attempts on your Cinema Star's account at &lt;&lt;Date &amp; Time&gt;&gt; from IP</td></tr><tr><td></td><td>address &lt;&lt;IP Address&gt;&gt;. For your security, your account has been temporarily locked for 15 minutes. After</td></tr><tr><td></td><td>15 minutes, you may log in again normally. If you forgot your password, please use the Forgot Password</td></tr><tr><td></td><td>option on the login page. If you did not make these attempts, we recommend resetting your password</td></tr><tr><td></td><td>immediately to protect your account.</td></tr><tr><td></td><td>Sincerely,</td></tr><tr><td></td><td>Cinema Star's Team</td></tr><tr><td></td><td>Note: This is an auto-generated email, please do not reply.</td></tr></table>

Note: This is an auto-generated email, please do not reply