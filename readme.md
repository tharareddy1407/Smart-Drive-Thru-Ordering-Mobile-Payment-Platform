# Smart Drive-Thru Ordering & Mobile Payment Platform
## Order and Pay Without Opening the Car Window

## Project Overview
This project is a real-time drive-thru ordering and mobile payment prototype designed to remove the need for customers to open their vehicle window for ordering or payment.

Customers complete the entire ordering and payment process on their mobile phone while remaining inside the vehicle. The window is opened only once, at the pickup window, to receive the order.

This system provides a mobile-first alternative to traditional drive-thru solutions that rely on outdoor microphones, verbal communication, and physical payment terminals.

## Who This Project Is For
This project is intended for:
- Quick-service restaurants (QSRs)
- Drive-thru technology and product teams
- Restaurant operations and innovation leaders
- Engineers and architects exploring real-time, mobile-first systems

## Key Differentiator
### No Window Interaction Until Pickup
Customers do not need to open their car window to:
- Place an order
- Communicate with the cashier
- Make a payment

All ordering and payment activities are completed on the customer’s phone. The window is opened only at the pickup window.

### Benefits
This approach improves:
- Comfort during rain, cold, or extreme heat
- Order accuracy in noisy environments
- Speed, safety, and efficiency of the drive-thru experience

## Why This Is a Smarter Approach
### Traditional Drive-Thru Systems Require
- Outdoor microphones and speakers
- Verbal ordering through open windows
- Physical payment terminals
- Multiple stop-and-go interactions

### This System Replaces Them With
- Secure lane-based mobile connection
- Real-time chat or browser-based voice calls
- Mobile payment completed before pickup

### Result
A simpler, faster, and more reliable drive-thru workflow with fewer hardware dependencies.

## Updated User Flow
1. Customer enters the drive-thru lane
2. Customer connects using the station code displayed at the lane
3. Customer places the order using mobile chat or voice
4. Customer completes payment on their phone
5. Customer opens the window only at the pickup window to receive the order

## Use Case
This solution works especially well for:
- Cold, rainy, or extreme weather conditions
- High-noise drive-thru environments
- Customers who prefer minimal interaction
- Restaurants seeking to reduce hardware and maintenance costs

It introduces a modern, contact-minimized drive-thru experience without changing normal customer behavior beyond using a smartphone.

## Technologies Used
- FastAPI for backend APIs and application server
- WebSockets for real-time chat, order updates, and payment status
- WebRTC for browser-based voice communication
- Python for backend logic and session management
- HTML, CSS, and JavaScript for customer, cashier, and lane interfaces
- Google STUN server for WebRTC network connectivity

## System Implementation Steps
### 1. Requirement Analysis
Identified limitations of traditional drive-thru systems, including window dependency, noise issues, and slow payment handling.

### 2. Architecture Design
Designed a mobile-first architecture where:
- Customers connect using a short lane code
- Ordering and payment happen inside the vehicle
- Cashiers manage all interactions from a single console

### 3. Backend Development
- Built REST APIs using FastAPI
- Implemented WebSocket-based real-time communication
- Created in-memory session handling for lanes, orders, and payments

### 4. Lane Code System
- Implemented rotating four-digit station codes
- Codes expire after ten minutes
- Codes rotate immediately after successful order creation

### 5. Customer Portal
- Lane check-in using station code
- Real-time chat and voice ordering
- Mobile payment selection and confirmation

### 6. Cashier Console
- Unified interface for managing orders and payments
- Real-time chat and voice call support
- Order total confirmation and payment request triggering

### 7. Voice Call Integration
- WebRTC signaling handled via WebSockets
- Browser-based voice communication
- Accept, reject, and hang-up controls

### 8. Payment Flow Simulation
- Demo payment session handling
- Multiple payment options supported
- Clear payment success confirmation for customers

### 9. Deployment and Testing
- Tested locally and on cloud platforms
- Verified mobile browser compatibility
- Validated real-time communication between customer and cashier

## Live Demo
### Website
https://easypay-kb8f.onrender.com

### Demo Pages
- Customer Portal  
  https://easypay-kb8f.onrender.com/customer
- Cashier Console  
  https://easypay-kb8f.onrender.com/cashier
- Lane Display  
  https://easypay-kb8f.onrender.com/lane/L1  
  https://easypay-kb8f.onrender.com/lane/L2

## Step-by-Step Demo Guide
### Step 1: Open the Lane Display
Open one of the lane display pages to view the four-digit station code.

### Step 2: Open the Customer Portal
- Select a lane
- Click “I’m Here”
- Enter the station code
- Click Connect

### Step 3: Open the Cashier Console
- Click Refresh Orders
- Select the active order
- Click Join

### Step 4: Place the Order
- Place the order via text chat or voice call
- Cashier responds in real time

### Step 5: Confirm Total and Pay
- Cashier confirms the total
- Customer selects a payment method
- Payment is completed on the phone

### Step 6: Pickup
- Customer opens the window only at the pickup window
- Order is already paid and confirmed

## Important Notes
- This project is a demo prototype
- No real payments are processed
- All data resets when the server restarts
- Best experience:
  - Customer: mobile browser
  - Cashier: laptop browser
- Chrome is recommended for voice calls

## Why This Is Different
Unlike traditional drive-thru systems:
- No window opening for ordering
- No shouting into microphones
- No payment at the window

Everything happens on the phone, inside the vehicle.

## Disclaimer
This project is a conceptual prototype intended for demonstration and idea validation only. It is not production-ready and does not process real payments.


