# Smart Drive-Thru Ordering & Mobile Payment Platform
Order and Pay Without Opening the Car Window

**Project Overview**
This project is a real-time drive-thru ordering and payment prototype designed to eliminate the need for customers to open their vehicle window for ordering or payment.
Customers complete the entire ordering and payment process on their mobile phone while remaining inside the vehicle. The window is opened only once, at the pickup window, to collect the order.
This approach represents a smarter, mobile-first alternative to traditional drive-thru systems that rely on outdoor microphones, cash handling, and in-person payment terminals.

**Who This Project Is For**
1.This project is relevant for:
* Quick-service restaurants (QSRs)
* Drive-thru technology and product teams
* Restaurant operations and innovation leaders
* Engineers and architects exploring real-time, mobile-first systems

**Key Differentiator**:
1.No Window Interaction Until Pickup
2.Customers do not need to open the car window to:
* Place an order
* Communicate with the cashier
* Make a payment
3.Ordering and payment are completed inside the vehicle using a phone. The window is opened only at the pickup window.
This significantly improves:
* Comfort during rain, cold, or extreme heat
* Order accuracy in noisy environments
* Speed and safety of the drive-thru experience

**Why This Is a Smarter Approach**
1.Traditional Drive-Thru Systems Require:
* Outdoor microphones and speakers
* Verbal ordering through open windows
* Physical payment terminals
* Multiple stop-and-go interactions
2.This System Replaces Those With:
* Secure lane-based mobile connection
* Real-time chat or voice call via phone
* In-app payment before pickup
**Result**: A simpler, faster, and more reliable drive-thru workflow with fewer hardware dependencies.

**Updated User Flow**
1. Customer enters the drive-thru lane
2. Customer connects using the station code shown at the lane
3. Customer orders food via mobile chat or voice call
4. Customer completes payment on their phone
5. Customer opens the window only at the pickup window to receive the order

**Use Case**
This solution is particularly effective for:
* Cold or rainy weather conditions
* High-noise drive-thru locations
* Customers who prefer minimal interaction
* Restaurants seeking to reduce hardware dependency
It introduces a modern, contact-minimized drive-thru experience without requiring changes to customer behavior beyond using a smartphone.

**Technologies Used**
* FastAPI – Backend APIs and application server
* WebSockets – Real-time chat, order updates, and payment status
* WebRTC – Browser-based voice calls (no phone numbers required)
* Python – Core backend logic and session management
* HTML, CSS, JavaScript – Customer portal, cashier console, and lane display UI
* STUN Server (Google) – WebRTC network connectivity support

**Steps: How This Project Was Created**
1. Requirement Analysis Identified limitations of traditional drive-thru systems such as window dependency, noise issues, and slow payment flow.
2. Architecture Design Designed a mobile-first system where:
    * Customers connect using a lane code
    * Ordering and payment occur inside the vehicle
    * Cashiers manage orders and payments from one console
3. Backend Development
    * Built REST APIs using FastAPI
    * Implemented WebSocket-based real-time communication
    * Created in-memory session handling for orders, payments, and lane codes
4. Lane Code System
    * Implemented rotating 4-digit station codes
    * Codes expire after 10 minutes
    * Codes rotate immediately after successful order creation
5. Customer Portal
    * Lane check-in flow
    * Secure connection using station code
    * Real-time chat and voice ordering
    * Mobile payment selection and confirmation
6. Cashier Console
    * Unified interface for order handling and payment
    * Real-time chat and voice call support
    * Order total confirmation and payment request triggering
7. Voice Call Integration
    * WebRTC signaling via WebSockets
    * Browser-based voice communication
    * Accept, reject, and hang-up controls
8. Payment Flow Simulation
    * Demo payment session handling
    * Multiple payment options supported
    * Clear payment success confirmation to customer
9. Deployment & Testing
    * Tested locally and on cloud platforms
    * Verified mobile browser compatibility
    * Validated real-time communication between customer and cashier

**Live Demo**
Website: 👉 https://easypay-kb8f.onrender.com
Demo Pages
* Customer Portal: https://easypay-kb8f.onrender.com/customer
* Cashier Console: https://easypay-kb8f.onrender.com/cashier
* Lane Display:
    * https://easypay-kb8f.onrender.com/lane/L1
    * https://easypay-kb8f.onrender.com/lane/L2

**Step-by-Step Guide**
Step 1: Open the Lane Display
Open one of the lane pages to view the 4-digit station code.
Step 2: Open the Customer Portal (Phone)
* Select lane
* Click “I’m Here”
* Enter the 4-digit code
* Click Connect
Step 3: Open the Cashier Console (Laptop)
* Click Refresh Orders
* Select the order
* Click Join
Step 4: Place the Order
* Order via text chat or voice call
* Cashier responds in real time
Step 5: Confirm Total & Pay
* Cashier confirms total
* Customer selects payment method
* Payment is completed inside the vehicle
Step 6: Pickup
* Customer opens the window only at the pickup window
* Order is already paid and confirmed

**Important Notes**
* This is a demo / prototype
* No real payments are processed
* Data resets when the server restarts
* Best experience:
    * Customer → Mobile browser
    * Cashier → Laptop browser
* Chrome recommended for voice calls

**Why This Is Different**
Unlike traditional drive-thru systems:
* No window opening for ordering
* No shouting into microphones
* No payment at the window
Everything happens on the phone, inside the vehicle.

**Disclaimer**
This project is a conceptual prototype intended for demonstration and idea validation only. It is not production-ready and does not process real payments.
