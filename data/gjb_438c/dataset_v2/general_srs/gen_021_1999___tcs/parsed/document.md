TCS 102Block 0   
Version 2.0   
TCS102   
2/12/99

# Tactical Control System (TCS) System/Subsystem Specification

![](images/534c7eca983f9513ec42e4eb8f2c84b4b5cd5e6fff1c1b22df10c800fde5e7c3.jpg)

Prepared for:

Program Executive Officer, Cruise Missiles Project and Unmanned Air Vehicles Joint Project

Prepared by:

Naval Surface Warfare Center-Dahlgren Division and Joint Technology Center/System Integration Laboratory, Research Development and Engineering Center, U.S. Army Missile Command, Redstone Arsenal, AL.

TCS Block 0   
Version 2.0   
12 February 1999

Approved by: TCS Program Manage

Date:

## DOCUMENT SIGNATURE PAGE

This document has been reviewed and accepted by the following:

<table><tr><td>TCS Deputy Program Manager, L. Baile</td><td>RAD IPT, D. Malloy</td></tr><tr><td>NSWCDD Program Manager, S. Parker</td><td>Software IPT, W. Sullivan</td></tr><tr><td>SIL Program Manager. S. McClung</td><td>System Development IPT, M. Henthorne</td></tr><tr><td>C4I IPT, B. Azzarelli</td><td>System Engineering IPT, S. Daniel</td></tr><tr><td>CM IPT, C. Simmons</td><td>System Test &amp; Demo IPT, Lt Col K. Nathaniel</td></tr><tr><td>Data Links IPT, S. Hussman</td><td>Training IPT, W. Malley</td></tr><tr><td>Logistics IPT, T. Piester</td><td>Warfighters Planning Group, M. Garrido</td></tr></table>

## Table of Contents

FIGURES.. ERROR! BOOKMARK NOT DEFINED.   
TABLES .VI   
ACRONYM LIST .VII   
CHAPTER 1 SCOPE.   
1.1 Identification ....   
1.2 System Overview....   
1.2.1 TCS Program, Phases, and UAV Interaction Error! Bookmark not defined.   
1.2.2 Tactical Control System Error! Bookmark not defined.   
1.2.2.1 Software . . 2   
1.2.2.2 Hardware. . 2   
1.2.3 Integration with Joint C4I Systems 2   
1.2.4 System Compliance. 3   
1.3 Document Overview... 4   
CHAPTER 2 REFERENCED DOCUMENTS.   
2.1 Government Documents ....   
2.2 Non-Government Documents ..   
CHAPTER 3 ENGINEERING REQUIREMENTS. 7   
3.1 Required States And Modes .... . 8   
3.1.1 Startup State . . 8   
3.1.1.1 Normal Startup Mode . 9   
3.1.1.2 Recovery Startup Mode . 9   
3.1.2 Operations State 10   
3.1.2.1 Normal Operations Mode. 10   
3.1.2.2 Training Operations Mode 11   
3.1.2.3 Maintenance Operations Mode 12   
3.1.3 Shutdown State. 13   
3.2 System Capability Requirements ... .. 13   
3.2.1 Mission Planning Function 13   
3.2.1.1 Flight Route Planning Capability 15   
3.2.1.1.1 Map Display Task. 16   
3.2.1.2 Payload Planning Capability 17   
3.2.1.3 Communications Planning Capability. 17   
3.2.2 Mission Control And Monitoring Functions. 17   
3.2.2.1 AV Control And Monitoring Capability 18   
3.2.2.1.1 AV Flight Control Task 18   
3.2.2.1.1.1 Flight Behavior Characteristics 19   
3.2.2.1.2 AV Navigation Control Task . 19   
3.2.2.1.3 ADT Control Task.. . 19   
3.2.2.1.3.1 ADT Antenna Control 19   
3.2.2.1.3.2 ADT Transmitter And Receiver Control . 19   
3.2.2.1.4 AV Launch/Recovery Task 19   
3.2.2.1.4.1 Emergency Recovery 19   
3.2.2.1.5 AV Monitoring Task. . 20   
3.2.2.1.5.1 AV Monitoring Displays 20   
3.2.2.2 Payload Control And Monitoring Capability 20   
3.2.2.2.1 Payload Control Task 21   
3.2.2.2.2 Payload Monitoring Task. . 21   
3.2.2.2.2.1 Payload Monitoring Displays . 21   
3.2.2.3 Data Terminal Control And Monitoring Capability . . 21   
3.2.2.3.1 Data Terminal Control Task. 21   
3.2.2.3.1.1 Antenna And Pedestal Control . 22   
3.2.2.3.1.2 Transmitter And Receiver Control 22   
3.2.2.3.2 Data Terminal Monitoring Task 22   
3.2.3 Payload Product Management Function. 23   
3.2.3.1 Payload Product Processing Capability. 23   
3.2.3.2 Payload Product Display Capability. . 23   
3.2.3.3 Payload Product Exploitation Capability 24   
3.2.4 Targeting Function. 24   
3.2.4.1 Target Coordinate Development Capability . 24   
3.2.4.2 Target Accuracy Estimation Capability.. . 24   
3.2.5 C4I System Interface Function . 25   
3.2.5.1 C4I Interface Control Capability . 26   
3.2.5.1.1 C4I Digital Interface Control Capability 26   
3.2.5.1.2 C4I Analog Interface Control Capability . 26   
3.2.5.2 C4I Interface Data Processing Capability 27   
3.2.5.2.1 C4I Digital Interface Data Processing Capability . 27   
3.2.5.2.2 C4I Analog Interface Data Processing Capability 27   
3.2.5.3 C4I Interface Monitoring Capability . 27   
3.2.6 AV Maintenance Function.. . 28   
3.2.7 Payload Maintenance Function . 28   
3.2.8 Data Terminal Maintenance Function . 28   
3.2.9 Workstation and Peripheral Equipment Maintenance Function. 28   
3.2.10 Fault Detection/Location Function . 28   
3.2.10.1 Startup FD/L 28   
3.2.10.2 Periodic FD/L 29   
3.2.10.3 Extensive FD/L . 29   
3.2.11 Software Upgrade Function. . 29   
3.2.12 Software Debug and Monitoring Function. . 30   
.3 System External Interface Requirements........ .... 30   
3.3.1 Interface Identification . 30   
3.3.1.1 TCS to C4I. . 30   
3.3.1.1.1 TCS to ASAS . 32   
3.3.1.1.2 TCS to JSTARS GSM. . 32   
3.3.1.1.3 TCS to JMCIS. . 32   
3.3.1.1.4 TCS to JSIPS-N . 32   
3.3.1.1.5 TCS to AFATDS . 32   
3.3.1.1.6 TCS to JSIPS-AF 32   
3.3.1.1.7 TCS to CARS. . 32   
3.3.1.1.8 TCS to CCTV . 33   
3.3.1.1.9 TCS to Service Mission Planners . 33   
3.3.1.1.9.1TCS to Army Mission Planning System . . 33   
3.3.1.1.9.2 TCS to Air Force Mission Support System . 33   
3.3.1.1.9.3 TCS to Tactical Aircraft Mission Planning System. . 33   
3.3.1.1.10 TCS to GCS/ACS IPF . 33   
3.3.1.1.11 TCS to JDISS . 33   
3.3.1.1.12 TCS to TES. . 33   
3.3.1.1.13 TCS to IAS . 34   
3.3.1.1.14 TCS to ATHS. . 34   
3.3.1.1.15 TCS to ATWCS . 34   
3.3.1.1.16 TCS to TROJAN SPIRIT II. 34   
3.3.1.1.17 TCS to TBMCS. 34   
3.3.1.1.18 TCS to MIES . 34   
3.3.1.1.19 TCS to ETRAC . 34   
3.3.1.1.20 TCS to COMPASS . 34   
3.3.1.1.21 TCS to TEG . . 35   
3.3.1.2 TCS to DT Control . 35   
3.3.1.3 TCS to Printer . . 35   
3.3.1.4 External Data Storage Systems . 36   
3.3.1.5 TCS to External Power . 36   
3.3.1.6 TCS to Geopositional Data . . 37   
3.4 System Internal Interface Requirements ... .. 37   
3.4.1 AV Standard Interface . 39   
3.4.2 Real Time Processor . 39   
3.4.2.1 Distributed Processing . 39   
3.4.3 SAR Processor. . 39   
3.4.4 Intercom . 39   
3.4.5 VCR . . 40   
3.4.6 Printer. . 40   
3.4.7 Data Storage Devices. 40   
3.4.7.1 CD Drive . . 40   
3.4.7.2 Tape Drive. . 40   
3.4.7.3 Redundant Array Of Inexpensive Disks (RAID) . 41   
3.4.8 Uninterruptible Power. 41   
3.5 System Internal Data Requirements . 41   
3.6 Adaptation Requirements... 41   
3.7 Safety Requirements ... . 41   
3.7.1 Air Vehicle Safety 41   
3.7.2 Human Safety . 42   
3.7.3 System Safety And Health Hazard Assets . 42   
3.8 Security And Privacy Requirements ... . 42   
3.8.1 Computer Security . 42   
3.8.2 Communications Security. . 43   
3.8.3 Physical Security . 43   
3.8.4 Personnel Security. . 43   
3.8.5 Privacy Requirements. . 43   
3.9 System Environment Requirements. .. 43   
3.10 Resource Requirements ... . 44   
3.10.1 Hardware Requirements . 44   
3.10.1.1 Performance. . 44   
3.10.1.2 Mass Storage . 44   
3.10.1.3 Power . . 44   
3.10.2 Hardware Resource Utilization Requirements. . 45   
3.10.3 Computer Software Requirements. . 45   
3.10.3.1 Display. . 46   
3.10.4 Computer Communication Requirements. . 46   
3.11 System Quality Factors... .. 47   
3.11.1 Functionality . 47   
3.11.2 Reliability. . 47   
3.11.3 Maintainability . 47   
3.11.4 Availability. . 48   
3.11.5 Flexibility . 48   
3.11.6 Portability . 48   
3.11.7 Reusability . 49   
3.11.8 Testability . 49   
3.11.9 Usability. . 49   
3.12 Design And Construction Constraints .... . 49   
3.12.1 Documentation. . 49   
3.12.2 Materials. . 50   
3.12.3 Electromagnetic Radiation. . 50   
3.12.4 Software . . 50   
3.12.5 Hardware . . 51   
3.12.6 Responsiveness . 51   
3.12.7 Endurance . 51   
3.13 Personnel-Related Requirements ..... .. 51   
3.13.1 Human Factors Engineering (HFE). . 51   
3.14 Training Related Requirements ... . 54   
3.15 Logistics-Related Requirements .. . 55   
3.15.1 Transportability 56   
3.15.1.1 Ground 56   
3.15.1.2 Air . . 56   
3.15.1.3 Sea . 57   
3.15.1.4 Rail . 57   
3.15.1.5 Preparation Time 57   
3.16 Other Requirements.... . 57   
3.17 Packaging Requirements . 57   
3.18 Precedence And Criticality Of Requirements.... .. 57   
4.0 QUALITY ASSURANCE PROVISIONS .59   
4.1 Responsibility for Inspections... . 59   
4.2 Special Tests and Examinations. . 59   
4.2.1 Government Verification. 59   
4.2.2 Integrated Test Program. 60   
4.3 Requirements Cross-Reference. 60   
APPENDIX A: REQUIREMENTS TRACEABILITY MATRIX .62   
APPENDIX B: MAE APPLICABLE CAPABILITY CRITERIA AND   
CHARACTERISTICS .99   
APPENDIX C: CR-TUAV APPLICABLE CAPABILITY CRITERIA AND   
CHARACTERISTICS.. .116

## Figures

FIGURE 3.1-1 TCS STATE DIAGRAM. . 8   
FIGURE 3.1.1-1 TCS STARTUP STATE AND ASSOCIATED MODES DIAGRAM. . 9   
FIGURE 3. 1.2-1 TCS OPERATIONS STATE AND ASSOCIATED MODES DIAGRAM 10   
FIGURE 3.1.2.1-1 TCS NORMAL OPERATIONS AND ASSOCIATED FUNCTIONS DIAGRAM 11   
FIGURE 3.1.2.2-1 TCS TRAINING MODE AND ASSOCIATED FUNCTIONS DIAGRAM 12   
FIGURE 3.1.2.3-1 TCS MAINTENANCE MODE AND ASSOCIATED FUNCTIONS DIAGRAM. 13   
FIGURE 3.3.1.1-1 TCS TO C4I INTERFACE DIAGRAM 31   
FIGURE 3.3.1.2-1 TCS TO DT CONTROL INTERFACE DIAGRAM. 35   
FIGURE 3.3.1.3-1 TCS TO PRINTER INTERFACE DIAGRAM. 35   
FIGURE 3.3.1.4-1 TCS TO EXTERNAL DATA STORAGE SYSTEM INTERFACE DIAGRAM 36   
FIGURE 3.3.1.5-1TCS TO EXTERNAL POWER INTERFACE DIAGRAM. 36   
FIGURE 3.3.1.6-1 TCS TO GEOPOSITIONAL DATA INTERFACE DIAGRAM 37   
FIGURE 3.4-1 TCS INTERNAL INTERFACE DIAGRAM. 38

## Tables

TABLE 3-17 INTEROPERABLE TCS PAYLOADS ........................... ERROR! BOOKMARK NOT DEFINED.

TABLE 3.3.1.1-1 C4I INTERFACE INTEGRATION PRIORITY SCHEDULEERROR! BOOKMARK NOT DEFINED.

TABLE 3.10.4-1 COMMUNICATION MEDIA AND ASSOCIATED INTERFACE DOCUMENTERROR! BOOKMARK NO

Acronym List
<table><tr><td>ADRG</td><td>Acronym List Arc Digitized Raster Graphic</td></tr><tr><td>ADT</td><td>Air Data Terminal</td></tr><tr><td>AFATDS</td><td>Advanced Field Artillery Tactical Data System</td></tr><tr><td>AFMSS</td><td>Air Force Mission Support System</td></tr><tr><td>AIS</td><td>Automated Information System</td></tr><tr><td>AMPS</td><td>Aviation Mission Planning System</td></tr><tr><td>ASAS</td><td>All Source Analysis System</td></tr><tr><td>ASD</td><td>Assistant Secretary of Defense</td></tr><tr><td>ATCSS</td><td>Army Tactical Command Control System</td></tr><tr><td>ATHS</td><td>Automated Target Hand-off System</td></tr><tr><td>ATO</td><td>Air Tasking Order</td></tr><tr><td>ATWCS</td><td>Advanced Tactical Weapons Control Station</td></tr><tr><td>AV</td><td>Air Vehicle</td></tr><tr><td>BITE</td><td>Built In Test Equipment</td></tr><tr><td>C4I</td><td>Command, Control, Communication, Computer, and Intelligence</td></tr><tr><td>CADRG</td><td>Compressed Arc Digitized Raster Graphic</td></tr><tr><td>CARS</td><td>Common Automated Recovery System</td></tr><tr><td>CARS</td><td>Contingency Airborne Reconnaissance System</td></tr><tr><td>CCTV</td><td>Closed Circuit Television</td></tr><tr><td>CD ROM</td><td>Compact Disk Read Only Memory</td></tr><tr><td>CIGSS</td><td>Common Imagery Ground/Surface System</td></tr><tr><td>COMSEC</td><td>Computer Security</td></tr><tr><td>COMPASS</td><td>Common Operational Modeling, Planning, and Simulation System</td></tr><tr><td>COSIP</td><td>Computer Open Systems Interface Processor</td></tr><tr><td>COTS</td><td>Commercial-Off-The-Shelf</td></tr><tr><td>CSC</td><td>Computer Software Component</td></tr><tr><td>CSCIs</td><td>Computer Software Configuration Items</td></tr><tr><td>CSU</td><td>Computer Software Unit</td></tr><tr><td>DCN</td><td>Document Control Number</td></tr><tr><td>DFAD</td><td>Digital Feature Analysis Data</td></tr><tr><td>DII/COE</td><td>Defense Information Infrastructure/Common Operating Environment</td></tr><tr><td>DoD</td><td>Department of Defense</td></tr><tr><td>DS</td><td>Data Server</td></tr><tr><td>DTED</td><td>Digital Terrain Elevation Data</td></tr><tr><td>EMI</td><td>Electromagnetic Interference</td></tr><tr><td>EO</td><td>Electro-Optic</td></tr><tr><td>ETRAC</td><td>Enhanced Tactical Radar Correlator</td></tr><tr><td>EW</td><td>Electronic Warfare</td></tr><tr><td>FAA</td><td>Federal Aviation Administration</td></tr><tr><td>FATDS</td><td>Field Artillery Tactical Data System</td></tr></table>

FD/L Fault Detection / Location   
FIPS Federal Information Processing Standard   
GCCS Global Command and Control Systems   
GCS Ground Control Station   
GCS/ACS Guardrail Common Sensor/Aerial Common Sensor   
GDT Ground Data Terminal   
GFE Government Furnished Equipment   
GPS Global Positioning System   
GSM/CGS Ground Station Module/Common Ground Station   
HAE High Altitude and Endurance   
HCI Human-Computer Interface   
HDD Hardware Design Document   
HFE Human Factors Engineering   
HWCIs Hardware Configuration Items   
IAS Intelligence Analysis System   
IAW In Accordance With   
IBLS Integrity Beacon Landing System   
IDD Interface Design Description   
IEEE Institute of Electrical and Electronics Engineers   
I/F Interface   
IFF Identification Friend or Foe   
ILSP Integrated Logistics Support Plan   
INS Inertial Navigation System   
IPF Integrated Processing Facility   
IR Infrared   
IRS Interface Requirements Specifications   
JMCIS Joint Maritime Command Information System   
JMF Joint Message Format   
JPO Joint Project Office   
JROC Joint Requirements Oversight Council   
JSIPS-N Joint Service Imagery Processing System - Navy   
JSTARS Joint Standoff Target Attack Radar System   
JTA Joint Technical Architecture   
LOL Loss of Link   
LOS Line of Sight   
LRIP Low Rate Initial Production   
LRP Launch and Recovery Point   
LRU Line Replaceable Unit   
MAE Medium Altitude and Endurance   
MGRS Military Grid Reference System   
MIES Modernized Imagery Exploitation System   
MOPP Mission Oriented Protective Posture   
MTBF Mean Time Between Failure   
MTTR Mean Time To Repair   
NDI Non-Developmental Items   
NIST National Institute for Standard Technology   
NITF National Imagery Transmission Format   
NRT Near-Real Time   
ORD Operational Requirements Document   
OT Operate Time   
POL Petroleum, Oil, Lubricants   
RAID Redundant Array of Inexpensive Disk   
SAR Synthetic Aperture Radar   
SATCOM Satellite Communication   
SPIRIT Special Purpose Integrated Remote Intelligence Terminal   
SPTE Special Purpose Test Equipment   
SRS Software Requirements Specification   
SSDD System/Subsystem Design Document   
SSS System / Subsystem Specification   
ST Stand-by Time   
TACCOM Tactical Communications   
TALDT Total Administrative and Logistic Downtime   
TAMPS Tactical Aircraft Mission Planning System   
TBD To Be Determined   
TBMCS Theater Battle Management Core System   
TCM Total Corrective Maintenance   
TCS Tactical Control System   
TCSEC Trusted Computer Security Evaluation Criteria   
TEG Tactical Exploitation Group   
TMDE Test, Measurement, and Diagnostic Equipment   
TPM Total Preventative Maintenance   
TUAV Tactical Unmanned Aerial Vehicle   
UAV Unmanned Aerial Vehicle   
UHF Ultra High Frequency   
USAF United States Air Force   
USIS United States Imagery Standards   
USMTF United States Message Text Format   
UTM Universal Transverse Mercator   
VCR Video Cassette Recorder   
VDD Version Description Document   
VHF Very High Frequency   
VMF Variable Message Format

## Chapter 1 Scope

## 1.1 Identification

This TACTICAL CONTROL SYSTEM (TCS) - SYSTEM / SUBSYSTEM SPECIFICATION (SSS) - VERSION 1.0 identifies, specifies, and establishes the detailed system requirements for the Tactical Control System as set forth by the OPERATIONAL REQUIREMENTS DOCUMENT FOR THE UNMANNED AERIAL VEHICLE (UAV) TACTICAL CONTROL SYSTEM (TCS) - VERSION 5.0. The SSS further specifies the methods to be used to ensure that each requirement has been met. Requirements pertaining to the TCS external interfaces are covered in separate Interface Design Descriptions (IDDs) to be published. The SSS is published IAW DID DI-IPSC-81431, dated 941205.

## 1.2 System Overview

The purpose of the TCS is to provide the military services with a single command, control, data receipt, data processing, data export and dissemination system that is interoperable with the family of all present and future tactical unmanned aerial vehicles. These UAVs shall include the Tactical Unmanned Aerial Vehicle (TUAV) and the Medium Altitude and Endurance (MAE) UAV (henceforth referred to as Outrider and Predator respectively), their associated payloads, and other network communication systems. TCS will also be capable of receiving and processing information from High Altitude and Endurance (HAE) UAVs, their associated payloads, future development UAVs and payloads.

## 1.2.1 TCS Program, Phases, and UAV Interaction

The Unmanned Aerial Vehicle Joint Project Office (UAV JPO) has undertaken development of a TCS for UAVs. Design and development of the TCS will be conducted in two phases. Phase 1 is defined as the Program Definition and Risk Reduction phase, and Phase 2 is defined as the Engineering and Manufacturing Development phase in accordance with Department Of Defense Instruction (DODI) - 5000.2R. During Phase 2, TCS Low Rate Initial Production (LRIP) will commence. Phase 1 will be a 24 month period and will demonstrate Level 1 through Level 5 interaction (as defined below) in an Incremental and Evolutionary strategy as described in accordance with MIL-STD-498. The five discrete levels of multiple UAV interaction to be provided by the TCS are:

Level 1: receipt and transmission of secondary imagery and/or data

Level 2: direct receipt of imagery and/or data

Level 3: control of the UAV payload in addition to direct receipt of imagery/data

Level 4: control of the UAV, less launch and recovery, plus all the functions of level three

Level 5: capability to have full function and control of the UAV from takeoff to landing

## 1.2.2 Tactical Control System

The TCS consists of the software, software-related hardware and the extra ground support hardware necessary for the control of the Outrider, and the Predator UAV, and future tactical UAVs. The TCS will also provide connectivity to specifically identified Command, Control, Communications, Computers, and Intelligence (C4I) systems. TCS will have the objective capability of receiving High Altitude Endurance (HAE) UAV payload information. Although developed as a total package, the TCS will be scaleable to meet the user's requirements for deployment. TCS will provide a common Human-Computer Interface (HCI) for tactical airborne platforms to simplify user operations, training, and facilitate seamless integration into the Services’ joint C4I infrastructure across all levels of interaction.

## 1.2.2.1 Software

The major focus of the TCS program is software. The software will provide the UAV operator the necessary tools for computer related communications, mission tasking, mission planning, mission execution, data receipt, data processing, limited data exploitation, and data dissemination. The software will provide a high resolution computer generated graphical user interface that enables a UAV operator trained on one system to control different types of UAVs or UAV payloads with a minimum of additional training. The TCS will operate in an open architecture and be capable of being hosted on computers that are typically supported by the using Service. Software developed will be Defense Information Infrastructure / Common Operating Environment (DII/COE) compliant, non-proprietary, and the architectural standard for all future tactical UAVs. To the extent possible, the TCS will use standard Department of Defense (DoD) software components to achieve commonality. TCS will provide software portability, scaleable functionality, and support for operational configurations tailored to the users’ needs.

## 1.2.2.2 Hardware

To the extent possible, the TCS will use standard DoD components in order to achieve commonality. The TCS will use the computing hardware specified by the service specific procurement contracts. The individual armed services will identify TCS computing hardware, the desired level of TCS functionality, the battlefield C4I connectivity, and the particular type of air vehicle and payloads to be operated depending upon the deployment concept and area of operations. TCS hardware must be scaleable or modular to meet varying Service needs. TCS hardware will permit long range communications from one TCS to another, data storage expansion, access to other computers to share in processing capability, and multiple external peripherals.

## 1.2.3 Integration with Joint C4I Systems

TCS integration with C4I systems will be accomplished through development of interfaces that permit information exchange between the TCS and specified C4I systems. TCS will be capable of entering DII/COE compliant networks. Network interoperability will include but not be limited to:

Advanced Tomahawk Weapons Control Station (ATWCS)

Advanced Field Artillery Tactical Data System (AFATDS)

All Source Analysis System (ASAS)

Automated Target Hand-off System (ATHS)

Closed Circuit Television (CCTV)

Common Operational Modeling, Planning, and Simulation Strategy (COMPASS)

Contingency Airborne Reconnaissance System (CARS)

Enhanced Tactical Radar Correlator (ETRAC)

Guardrail Common Sensor/Aerial Common Sensor (ACS) Integrated Processing Facility (IPF)

Intelligence Analysis System (IAS)

Joint Deployable Intelligence Support System (JDISS)

Joint Maritime Command Information System (JMCIS)

Joint Service Imagery Processing System – Air Force (JSIPS-AF)

Joint Service Imagery Processing System - Navy (JSIPS-N)

Joint Surveillance Target Attack Radar System (JSTARS) Ground Station Module/Common Ground Station (GSM/CGS)

Modernized Imagery Exploitation System (MIES)

Service Specific Mission Planners

\- Army Mission Planning System (AMPS)

\- Air Force Mission Support System (AFMSS)

\- Tactical Aircraft Mission Planning System (TAMPS)

Tactical Exploitation Group (TEG)

Tactical Exploitation Systeme (TES)

Theater Battle Management Core System (TBMCS)

TROJAN Special Purpose Integrated Remote Intelligence Terminal (SPIRIT) II

Table 3.3.1.1-1 shows the planned implementation schedule for C4I interface realization. The TCS will export and disseminate UAV imagery products, tactical communication messages, as well as mission plans and target coordinates. The TCS will also receive, process, and display tasking orders, and operational information from Service specific mission planning systems.

## 1.2.4 System Compliance

The TCS will be developed in compliance with the following military and commercial computing systems architecture, communications processing, and imagery architecture standards:

a) Defense Information Infrastructure (DII) / Common Operating Environment (COE)

b) Computer Open Systems Interface Processor (COSIP)

c) Common Imagery Ground/Surface System (CIGSS) Handbook

d) Variable Message Format (VMF) and Joint Message Format (JMF)

e) National Imagery Transmission Format (NITF)

f) Assistant Secretary of Defense (ASD) (C3I) Joint Technical Architecture (JTA)

## 1.3 Document Overview

This section has been tailored out. See Table of Contents.

# Chapter 2 Referenced Documents

## 2.1 Government Documents

Only documents that are directly referred to in this document are included in the document lists.

1. MIL-STD-2500A Military Standard National Imagery Transmission Format (Version 2.0), 18 June 1993.

2. MIL-STD-498 Software Development and Documentation, 5 December 94.

3. Operational Requirements Document for the Unmanned Aerial Vehicle Tactical Control System (Version 5.0)

4. Operational Requirements Document (ORD) for the Tactical Unmanned Aerial Vehicle (TUAV), October 96

5. Operational Requirements Document (ORD) for the Medium Altitude Endurance (MAE) Unmanned Aerial Vehicle, (Not available for publication at this time)

6. Operational Concept Document for Tactical Control System (TCS), 18 February 1997.

7. MIL-STD-1472 Human Engineering Design Criteria for Military Systems, Equipment, and Facilities.

8. MIL STD 882 Safety

9. UAV TCS Program Management Plan (Version 1), 19 February 1997

10. Joint Requirements Oversight Council (JROC) Memorandum

11. TCS - C4I Interface Design Description

Tactical Control System (TCS) to Army Mission Planning System (AMPS) IDD, TCS 235

a. TCS to Advanced Tomahawk Weapons Control System (ATWCS) IDD, TCS 203

c. TCS to Advanced Field Artillery Tactical Data System (AFATDS) IDD, TCS 200

d. TCS to Air Force Mission Support System (AFMSS) IDD, TCS 220

e. TCS to All Source Analysis System (ASAS) IDD, TCS 201

f. TCS to Automated Target Hand-off System (ATHS) IDD, TCS 208

g. TCS to Closed Circuit Television (CCTV) IDD, TCS 205

h. TCS to Common Operational Modeling, Planning, and Simulation Strategy (COMPASS) IDD, TCS 222

i. TCS to Contingency Airborne Reconnaissance System (CARS) IDD, TCS 217

j. TCS to Enhanced Tactical Radar Correlator (ETRAC) IDD, TCS 218

k. TCS to Guardrail Common Sensor/Aerial Common Sensor (ACS) Integrated Processing Facility (IPF) IDD, TCS 215

l. TCS to Intelligence Analysis System (IAS) IDD, TCS 206

m. TCS to Joint Deployable Intelligence Support System (JDISS) IDD, TCS 212

n. TCS to Joint Maritime Command Information System (JMCIS) IDD, TCS 214

o. TCS to Joint Service Imagery Processing System - Air Force (JSIPS-AF) IDD, TCS 211

p. TCS to Joint Service Imagery Processing System - Navy (JSIPS-N) IDD, TCS 210

q. TCS to Joint Surveillance Target Attack Radar System (JSTARS)Ground Station

Module/Common Ground Station (GSM/CGS) IDD, TCS 209

r. TCS to Modernized Imagery Exploitation System (MIES) IDD, TCS 216

s. TCS to Tactical Aircraft Mission Planning System (TAMPS) IDD, TCS 219

t. TCS to Tactical Exploitation Group (TEG) IDD, TCS 207

u. TCS to Tactical Exploitation System (TES) IDD, TCS 236

v. TCS to Theater Battle Management Core System (TBMCS) IDD, TCS 221

w. TCS to TROJAN Special Purpose Integrated Remote Intelligence Terminal (SPIRIT) II IDD, TCS 213

12. TCS to Integrated Data Terminal IDD, TCS 237

13. TCS to Printer IDD, TCS 255

14. TCS to External Data Storage IDD, TCS 256

15. AV Standard IDD, TCS 229

16. TCS NRT to Data Server IDD, TCS 238

17. TCS to SAR Processor IDD, TCS 240

18. TCS to Intercom IDD - TCS 253

19. TCS to VCR IDD, TCS 246

20. TCS TEMP, TCS 101.

## 2.2 Non-Government Documents

(None)

## Chapter 3 Engineering Requirements

![](images/2717ffcaff2d962eeaa3392ff52b7672e357fb3f0dbdac512de58225661c6e56.jpg)  
Table 3-2 identifies the payloads with which the TCS shall be interoperable. [SSS013]  
Table 3-2 Interoperable TCS Payloads

<table><tr><td rowspan=1 colspan=1>PAYLOAD TYPE</td><td rowspan=1 colspan=1>UAV</td></tr><tr><td rowspan=1 colspan=1>EO/IR</td><td rowspan=1 colspan=1>Predator</td></tr><tr><td rowspan=1 colspan=1>SAR</td><td rowspan=1 colspan=1>Predator</td></tr><tr><td rowspan=1 colspan=1>EO/IR</td><td rowspan=1 colspan=1>Outrider</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Future</td></tr></table>

## 3.1 Required States And Modes

The states of operation of the TCS shall include Startup, Operation, and Shutdown. [SSS014] The TCS states shall not exist concurrently. [SSS015] Figure 3.1-1 shows the existing states of the TCS.

![](images/5b93b31356e285cb5933420b9a48d2d250909622bddc6b4f644011bc027f1cef.jpg)  
Figure 3.1-1 TCS State Diagram

## 3.1.1 Startup State

Upon application of power the TCS shall enter the Startup State. [SSS016]

The Startup State shall be comprised of the following modes: Normal Startup Mode and Recovery Startup Mode. [SSS017]

Figure 3.1.1-1 shows the modes that exist in the Startup State.

![](images/a37c4ab738d9243240ac2c4bb0d574459296c10290029f47c0fbb1d029a17422.jpg)  
Figure 3.1.1-1 TCS Startup State and Associated Modes Diagram

The TCS will execute the particular startup mode which corresponds with the manner in which the TCS Software was halted.

When the TCS Software is terminated normally the TCS shall enter the Normal Startup Mode of operation upon application of power. [SSS019]

When the TCS software is halted due to an unplanned power interruption as well as abnormal program termination, then the TCS shall enter the Recovery Startup Mode upon application of power. [SSS020]

During startup, the TCS shall determine which of the 5 levels of interaction are achievable by the TCS configuration. [SSS021]

Levels of interaction higher than those achievable by a particular TCS configuration shall be prohibited. [SSS022]

The TCS shall inform the operator if the operator attempts to execute a function prohibited as a result of the determined level of interaction. [SSS023]

## 3.1.1.1 Normal Startup Mode

When executing in the Normal Startup Mode, the TCS shall provide the system functionality necessary to initialize the system to place it in the Operations State within 60 seconds from the time power is supplied and the TCS application is launched. [SSS024]

Initialization of the TCS HWCIs shall include startup of HWCIs [SSS542], download of software [SSS026], startup of CSCIs [SSS027], execution of Startup FD/L [SSS025], and establishment of the state of readiness of all interfaces. [SSS028]

## 3.1.1.2 Recovery Startup Mode

The TCS in the Recovery Startup Mode shall provide the system functionality to resume the Operations State within 45 seconds. [SSS029]

Recovery of the TCS HWCIs shall include startup of HWCIs [SSS543], download of software [SSS544], startup of CSCIs [SSS545], and establishment of the state of readiness of all interfaces. [SSS546]

The TCS shall be capable of automatically recording system state data, interface communications and other information necessary to support event reconstruction. [SSS528]

\*\*DELETED\*\*. [SSS030]

For recovery from abnormal termination, TCS shall prompt the operator to select the type of recovery to be executed: (1)Resume in the Same Modes And Data; (2)Resume in the Same Modes but Review and Modify the Command Data as Necessary; or, (3) Perform a Command Shutdown and Startup Via the Normal Startup Mode. [SSS031]

## 3.1.2 Operations State

When in the Operations State the TCS shall be capable of operating in three modes: normal operations mode, training operations mode, and maintenance operations mode. [SSS032]

Figure 3.1.2-1 shows the Mode Diagram for the Operations State of TCS.

![](images/fd2825e382ec3d38906de74d0d5919b58ef8bcf4ce00e89aa640c20295934d2b.jpg)  
Figure 3. 1.2-1 TCS Operations State and Associated Modes Diagram

The Operations State modes shall not exist concurrently. [SSS033]

The operator shall have the capability to command the system to the Shutdown State from all modes under the Operations State. [SSS035]

The TCS hardware and software shall execute periodic Fault Detection/Location (FD/L) while in the Normal Operations Mode and Training Mode, to include a periodic determination of level of interaction. [SSS036]

## 3.1.2.1 Normal Operations Mode

In the Normal Operations Mode the TCS shall support the following functions: [SSS037]

1. Mission Planning   
2. Mission Control and Monitoring   
3. Payload Product Management   
4. Target Coordinate Development   
5. C4I Systems Interface

Functions under the Normal Operations Mode shall operate concurrently without precluding or excluding any of the other functions, in accordance with allowable operations as determined by the appropriate levels of interaction. [SSS038]

Figure 3.1.2.1-1 shows the functions that exist under the Normal Operations Mode.  
![](images/45bd46f9873d9d5ba0193aaa7b0ca48b4f02f96a12c56dcff62b680d57792350.jpg)  
Figure 3.1.2.1-1 TCS Normal Operations and Associated Functions Diagram

## 3.1.2.2 Training Operations Mode

In the Training Operations Mode the TCS shall support the following functions: [SSS039]

1. Mission Planning

2. Mission Control and Monitoring

3. Payload Product Management

4. Target Coordinate Development

5. C4I Systems Interface

Functions under the Training Operations Mode shall operate concurrently without precluding or excluding any of the other functions, in accordance with allowable operations as determined by the appropriate levels of interaction. [SSS040]

Figure 3.1.2.2-1 shows the functions that exist under the Training Operations Mode.  
![](images/53a2907370df837274af6e412e328a85aa1169574bfb38c9c15782931e72e0ac.jpg)  
Figure 3.1.2.2-1 TCS Training Mode and Associated Functions Diagram

## 3.1.2.3 Maintenance Operations Mode

In the Maintenance Operations Mode, if computer workstation Human Computer Interface (HCI) is required, the TCS shall support the following functions: [SSS041]

1. Conduct AV maintenance

2. Conduct payload maintenance

3. Conduct Data Link Terminal maintenance

4. Conduct workstation and peripheral equipment maintenance

5. Perform Fault Detection/Location (FD/L)

6. Perform Software Upgrades

7. Perform Software Debug and Monitoring

Functions, except for software upgrade and software debug, under the Maintenance Operations Mode shall operate concurrently without precluding or excluding any of the other functions in accordance with allowable operations as determined by the appropriate levels of interaction. [SSS042]

Figure 3.1.2.3-1 shows the functions that exist under the Maintenance Operations Mode.  
![](images/aa8af760f0be5e0e6094be01a47d65fe82f1abbff07dfd771d467f7057292fbd.jpg)  
Figure 3.1.2.3-1 TCS Maintenance Mode and Associated Functions Diagram

## 3.1.3 Shutdown State

Upon the selection of a shutdown command the TCS shall enter the Shutdown State, which will cause the TCS to be placed in a condition where power can be removed without impacting operations as well as causing damage to the system, and from which restart of the system can be accomplished normally. [SSS043]

Shutdown of the TCS shall include storage as well as deletion, as specified by the operator, of mission data files [SSS044], shutdown of appropriate functions [SSS045], shutdown of HCIs [SSS046], and proper termination of all active interfaces [SSS047].

There shall be no modes of operation in the shutdown state. [SSS048]

## 3.2 System Capability Requirements

The TCS will provide the hardware and software necessary to allow the operator to conduct the following major functions 1) mission planning, 2) mission control and monitoring, 3) payload product management, 4) targeting, and 5) C4I system interface.

## 3.2.1 Mission Planning Function

The TCS shall have the functionality to allow the operator to generate a UAV mission plan. [SSS050]

The TCS shall have the functionality to receive and process UAV mission plans from service specific mission planning systems. [SSS053]

The TCS Mission plan shall include all necessary information required to be interoperable with the service specific mission planning systems including the Tactical Aircraft Mission Planning System (TAMPS), Aviation Mission Planning System (AMPS), and Air Force Mission Support System (AFMSS). [SSS051]

The TCS shall have the functionality to transmit UAV mission plans to service specific mission planning systems. [SSS055]

The TCS shall facilitate automated processing of mission plan data received via C4I interfaces in order to extract the appropriate mission planning data. [SSS052]

The TCS shall have the functionality to receive and process UAV mission plans from other TCSs. [SSS054]

The TCS shall have the functionality to transmit UAV mission plans to other TCSs. [SSS056]

A Mission Plan shall include a Flight Route Plan for a selected AV, a Payload Plan for the selected payload, and a Communications Plan. [SSS057] A Flight Route Plan is defined in Section 3.2.1.1. A Communications Plan is Defined in Section 3.2.1.3. A Payload Plan is defined in section 3.2.1.2.

The TCS shall be capable of storing a minimum of 500 mission plans under unique names to allow for later retrieval. [SSS058]

The TCS mission planning function shall provide a graphical user interface that gives the operator the ability to define waypoints on a map based display using a pointing device with full keyset redundancy. [SSS059]

The TCS shall provide the capability to compute the range and bearing between two geographic positions on the map display. [SSS561].

As an objective, the TCS shall have the capability to import as well as create and modify map display overlays for fire support coordination measures [SSS547], airspace control measures [SSS548], and threat identification measures. [SSS060]

Upon completion of radar cross section analysis and characterization by the Government for each UAV type, TCS shall utilize a UAV signature versus threat lookup table (database) that identities the lethality of the threat to the UAV [SSS065], and shall provide the capability of displaying aircraft signature versus threat, before and during flight. [SSS066]

The TCS shall permit dynamic mission and payload retasking during all phases of operational mission execution. [SSS067]

The TCS shall allow the operator to enter as well as review mission plan parameters, including AV flight parameters, payload control parameters, data link control parameters, AV VCR control parameters (if applicable to the selected AV), and AV loiter patterns. [SSS068]

The TCS shall provide the capability to enter system configuration characteristics in the mission plan, to include selected AV type, AV identification number, selected payload type, ground control authorization information, and required communications pre-set for data links, tactical communications, and C4I data dissemination. [SSS069]

The TCS shall provide the system functionality necessary to upload a flight route plan and payload plan (if applicable) to the AV via the selected system data link as well as direct ground connection. [SSS070]

TCS shall provide the capability for the operator to retrieve a mission plan for viewing, modification, as well as deletion at the operator's discretion [SSS071], and allow the operator to save the mission plan under a different name, for future retrieval [SSS072].

The TCS shall automatically check the validity of the intended mission plan prior to being uploaded including altitude constraints, payload constraints, data link range constraints, airspace restrictions, fuel limitations, threat constraints, data link terrain masking effects, and Loss of Link (LOL) Plan. [SSS073]

The TCS shall notify the operator of all discrepancies found during the mission plan check as well as indicate successful completion of the mission plan check. [SSS074]

The TCS shall provide the capability to override validation faults after the fault is acknowledged by the operator. [SSS540]

The TCS shall allow the operator to set the LOL delay timer(s) during mission planning. [SSS075] The LOL delay is the time from when the AV detects an unplanned LOL to the time it initiates LOL procedures.

The TCS shall provide the capability to print waypoint data in alphanumeric format. [SSS553]

## 3.2.1.1 Flight Route Planning Capability

The Flight Route Plan, as a minimum, shall include AV flight path information, Loss of Link plan, AV VCR control tasking (if applicable to the selected AV), and data link control information. [SSS079]

The TCS shall allow the operator to define the desired AV route in waypoint format [SSS551], and shall provide the capability to include up to 500 waypoints in each flight route plan. [SSS080]

The TCS shall provide the capability to display mission waypoints and flight path graphically. [SSS081]

The TCS shall provide the capability to enter waypoint data in alphanumeric format. [SSS082]

The TCS flight route planner shall include, as a minimum, the following flight planning tools:

1. Weight and balance take off data calculations. [SSS083]

2. Fuel Calculations. [SSS084]

3. Terrain avoidance warning for line of sight flights. [SSS085]

4. Minimum data link reception altitude calculations for line of sight flights. [SSS554]

5. Payload search area information such as: visual acuity range due to atmospheric conditions, diurnal transition periods for thermal imagery, and lunar and solar terrain shadowing. [SSS086]

6. Ability to designate flight corridors and restricted air space. [SSS087]

The TCS shall present to the operator the estimated time of arrival and fuel status at each programmed waypoint of the proposed mission plan. [SSS088]

At every waypoint and every 5 minutes, the TCS shall compute the AV's flight range based on remaining fuel. [SSS076]

The TCS shall analyze the flight route plan selected for uplink to determine that the flight constraints of the AV and the limitation of the data link are not violated prior to transmission of the flight route plan to the AV. [SSS089]

The algorithmic accuracy of all flight planning calculations shall not deviate by more than 10% when compared with a mission flown by a validated 6 degree-of-freedom air vehicle simulator. [SSS090]

The flight route plan, as a minimum, shall provide the necessary AV commands to autonomously execute a programmed flight and return to a designated recovery area. [SSS091]

The TCS shall provide the operator with an interactive graphics and map based flight route planning capability. [SSS092]

The TCS shall provide the capability to create waypoints that define the desired flight path, define AV Altitude and Airspeed associated with the waypoint. [SSS093]

## 3.2.1.1.1 Map Display Task

The TCS shall provide the capability of displaying overlays each containing 100 simultaneous icons of known fire support coordination zones [SSS549], airspace control zones [SSS550], threat systems [SSS061], and displaying the threat engagement envelopes with associated radar terrain masking for those threats [SSS062].

A de-clutter capability shall be provided that allows the operator to display only a selected number of the most significant threats. [SSS063]

The TCS shall provide the capability to modify the maximum number of threats displayed, when de-clutter is selected. [SSS064]

The TCS shall provide the capability to display waypoint data in alphanumeric format. [SSS552]

The TCS shall have the capability to load a map onto the display, to zoom in and out, to scroll, to print, and to clear a map on the map display. [SSS095]

The TCS shall provide the operator with a clearly indicated map scale. [SSS535]

Upon operator request, the following icons shall be displayed on the map display (when the coordinates reside on the displayed portion of the map).

1. Display an icon indicating AV position when receiving downlink from the desired AV. [SSS096]

2. Display an icon indicating payload center field of view and footprint when receiving downlink from the desired AV. [SSS097]

3. Display an icon, in variable sizes, indicating target position and type at coordinates selected by the operator. [SSS098]

4. Display icons indicating TCS position and Ground Data Terminal (GDT) position. [SSS099]

5. Display an icon indicating Launch, Handover, and Recovery site (when applicable). [SSS100]

6. Display icons indicating Flight Plan waypoints. [SSS101]

The TCS shall be capable of displaying the positions of the icons in Lat./Lon., Universal Transverse Mercator (UTM), and Military Grid Reference System (MGRS) formats and provide conversion to multiple spheroid scales. [SSS102]

The TCS shall provide the capability to graphically display Line of Sight versus terrain profile (DTED). [SSS538]

## 3.2.1.2 Payload Planning Capability

For those payloads identified in Table 3-2, the TCS shall be able to generate payload planning information to be uplinked to the AV separate from a flight route plan. [SSS103]

The TCS shall provide the system functionality necessary to generate a payload plan that, as a minimum, shall include the following information: [SSS104]

1. Payload type

2. Payload commands

3. Payload mode settings

4. Payload pointing commands, manual as well as automated

5. Payload field of view settings, manual as well as automated

The TCS shall provide the capability to display the payload swath for the selected payload for planning purposes. [SSS541]

## 3.2.1.3 Communications Planning Capability

\*\*DELETED\*\* [SSS105]

\*\*DELETED\*\* [SSS106]

\*\*DELETED\*\* [SSS107]

## 3.2.2 Mission Control And Monitoring Functions

The TCS will have the capability to control and monitor an AV, payload, data link, and C4I interfaces during the execution of a mission.

While flying two MAE AVs Beyond Line Of Sight (BLOS), the TCS shall provide full control functionality of each AV. [SSS108]

AV specific components used to perform ground based closed loop command and control functions for

TCS shall be initialized upon operator selection of a specific AV. [SSS109]

The TCS shall transmit command and control information to the AV via the uplink to the AV [SSS110], and receive AV telemetry and payload information via downlink from the AV [SSS111].

## 3.2.2.1 AV Control And Monitoring Capability

The TCS shall be capable of being interoperable with Predator and Outrider UAVs across the 5 levels of UAV interaction. [SSS011]

The TCS shall have the capability to control and monitor multiple types of AVs. [SSS112]

TCS shall notify the operator when AV performance parameters are out of limits. [SSS113]

The TCS shall provide the capability to pass control of an AV to another TCS [SSS114], and receive control of an AV from another TCS [SSS115].

The TCS shall provide the capability to control the AV flight commands as well as to release the AV to an autonomous flight control mode. [SSS118]

AV telemetry data shall be available to support other TCS functions as required. [SSS119]

The TCS shall provide the capability to control the flight of the selected AV in accordance with the specific AV's operational performance capabilities. [SSS120]

The TCS shall provide the capability to fully control and display the AV's Identification Friend or Foe (IFF). [SSS121]

The TCS shall provide the capability to enter AV preset limits which, as a minimum, will include airspeed limits, altitude limits, and fuel limits. [SSS122]

## 3.2.2.1.1 AV Flight Control Task

The TCS shall allow the operator to control an AV using the LOS as well as SATCOM data links. [SSS124]

The TCS shall provide the necessary system capabilities required for AV flight control BLOS via uplink command to two MAE air vehicles. [SSS125]

The TCS shall support operation of the AV via all flight modes, to include manual controls. [SSS126102]

The TCS shall provide the capability to implement an emergency action plan, if supported by the AV, to control the AV during equipment failures. [SSS539]

The TCS shall provide interactive displays necessary to command the flight of an AV. [SSS127]

## 3.2.2.1.1.1 Flight Behavior Characteristics

The TCS shall allow the operator to command the flight behavior characteristics inherent to the selected AV. [SSS128]

The operator shall have the capability to initiate as well as change, to include as a minimum manual override, flight behaviors by sending the proper control commands to the UAV. [SSS129]

## 3.2.2.1.2 AV Navigation Control Task

The TCS shall have the capability to command the AV to use the navigation methods inherent to the selected AV. [SSS130]

The operator shall have the capability to initiate as well as change, to include as a minimum manual override, UAV navigation methods by sending the proper control commands to the UAV. [SSS131]

## 3.2.2.1.3 ADT Control Task

The TCS shall provide the functionality to control, monitor, and display the operation of the Air Data Terminal (ADT). [SSS132] This control will include control of the ADT antenna and of the ADT transmitter and receiver.

## 3.2.2.1.3.1 ADT Antenna Control

The TCS shall provide the functionality to control the ADT antenna. [SSS133] This control will including its pointing direction and mode of transmission (e.g. omni and directional).

## 3.2.2.1.3.2 ADT Transmitter And Receiver Control

The TCS shall provide the functionality to control the power, transmitter signal strength, and frequencies used by ADT for data link communication. [SSS134]

## 3.2.2.1.4 AV Launch/Recovery Task

As an objective, the TCS shall support an automatic launch and recovery system. [SSS135]

As and objective, the TCS shall be interoperable with the Integrity Beacon Landing System (IBLS) [SSS136], and the Common Automated Recovery System (CARS) [SSS137], both used by Outrider.

As an objective, the TCS shall present sufficient cues to the operator to implement and monitor automatic launch and recovery, and to initiate abort procedures if required. [SSS138]

## 3.2.2.1.4.1 Emergency Recovery

The TCS shall allow the operator to initiate the emergency recovery feature of the AV, if the AV has an emergency recovery feature. [SSS139]

## 3.2.2.1.5 AV Monitoring Task

TCS shall provide the capability to monitor specific telemetry elements real-time, and record all telemetry elements for future review and processing. [SSS140]

TCS shall provide the capability to monitor AV adherence to the uplinked mission plan, detecting any deviations greater than 10% from projected flight path, and notifying the operator if deviations are detected. [SSS141]

TCS shall provide the capability to monitor the status of all AV subsystems reporting status. [SSS142]

## 3.2.2.1.5.1 AV Monitoring Displays

The TCS shall display the AV status, to include but not be limited to the AV location and flight and avionics system status. [SSS143]

When the data link is interrupted, the TCS shall present the last known AV status values and the time at which the last values were reported. [SSS144]

The TCS shall be capable of displaying fuel parameters to the operator to include as a minimum, remaining fuel, flow rate, and bingo fuel. [SSS145] Bingo fuel is the minimum amount of fuel necessary to return to the designated Recovery site with reserve fuel.

The TCS shall compute the estimated position of the AV during Loss of Link (LOL) based upon the last known AV position and anticipated flight path based on current flight mode (e.g. flight route plan mode, emergency flight route plan mode, maintain current heading mode). [SSS146]

TCS shall display a LOL timer to the operator initiating a LOL onset. [SSS536]

## 3.2.2.2 Payload Control And Monitoring Capability

The TCS shall be capable of being interoperable with the installed payloads across the 5 levels of UAV interaction. [SSS012]

The TCS will have the capability to control and monitor the AV payload(s). [SSS147]

The TCS shall have the capability to receive data from and control payloads on an AV that is being controlled from another TCS. [SSS148]

The TCS shall provide the necessary system capabilities required for payload control beyond line of sight via uplink command of two air vehicles of the same type using sequential communication techniques. [SSS149] Sequential communication means alternatively communicating with one air vehicle and then the other. Current air vehicle design does not permit concurrent communications with two air vehicles at the same time.

The TCS shall receive, process, and present payload data to the operator so that the status of the payload can be determined. [SSS151]

## 3.2.2.2.1 Payload Control Task

The TCS shall permit the operator to control the payload using all methods supported by the payload installed in the selected AV. [SSS152]

The TCS shall provide a graphical user interface display for the purpose of controlling the payload. [SSS153]

The TCS shall provide override of payload automated as well as preprogrammed inputs. [SSS154]

## 3.2.2.2.2 Payload Monitoring Task

TCS shall provide the capability to monitor payload adherence to the uplinked mission plan. [SSS155]

## 3.2.2.2.2.1 Payload Monitoring Displays

The TCS shall display the current search footprint and the search history of the payload on the map. [SSS157]

## 3.2.2.3 Data Terminal Control And Monitoring Capability

The TCS shall have the capability to simultaneously control and monitor a line-of-sight as well as a BLOS data terminal. [SSS158]

The TCS shall provide the system functionality necessary to record data obtained via the data link. [SSS527]

## 3.2.2.3.1 Data Terminal Control Task

The TCS shall be capable of interfacing with the specified data terminal and issuing data link terminal commands required to establish, control, and maintain the data link with a selected AV. [SSS159]

Data terminal control shall include, but is not limited to, antenna pointing control, transmitter control, and receiver control. [SSS160]

The TCS shall be capable of automatically selecting the proper mode of operation for the selected data terminal. [SSS161]

As a minimum the TCS LOS data terminal control modes shall include acquisition, autotrack, search, manual point, omni directional, as well as directional modes of operation, if applicable to the selected data link. [SSS162]

The operator shall be able to manually override any automatic data terminal control mode selection if desired, except during Emission Control (EMCON) and Hazards of Electromagnetic Radiation to Ordnance (HERO) conditions. [SSS163]

The TCS shall support a LOS data link and SATCOM data link capability. [SSS164]

For shipboard operations, the TCS shall provide the capability to switch to a second LOS antenna, if a second antenna is available, when desired (e.g. the currently active antenna is masked by shipboard obstructions). [SSS116]

The TCS shall provide the capability to switch to a SATellite COMmunication (SATCOM) antenna, if the selected AV has SATCOM capability, when desire (e.g. the AV proceeds beyond LOS range as well as when LOS is obstructed). [SSS117]

The TCS shall provide an interactive display for the purpose of controlling the data link terminal. [SSS165]

## 3.2.2.3.1.1 Antenna And Pedestal Control

The TCS shall provide automatic pointing commands for directional antennas [SSS167], and shall allow for the manual pointing of directional antennas when desired by the operator [SSS168].

The TCS shall be capable of positioning antennas to maintain LOS as well as SATCOM. [SSS170]

The TCS shall incorporate antenna pedestal 3 -axis stabilization to compensate for platform (e.g. ship, or HMMWV) motion, if applicable. [SSS557]

## 3.2.2.3.1.2 Transmitter And Receiver Control

The TCS shall be capable of automatically controlling the transmitter and receiver functions of the selected data terminal. [SSS171]

The operator shall be able to manually override the automatic function selection of the selected data terminal, if desired. [SSS172]

The TCS shall be capable of automatically controlling the transmitter and receiver modes of the selected data terminal. [SSS173]

The operator shall be able to manually override the automatic mode selection of the selected data terminal, if desired. [SSS174]

The TCS shall be capable of automatically controlling the transmitter and receiver frequencies of the selected data terminal. [SSS175]

The operator shall be able to manually override the automatic frequency selection if desired. [SSS176]

## 3.2.2.3.2 Data Terminal Monitoring Task

The TCS shall receive, process, and present status data to the operator so that the status of the data terminal and the supported AV data link can be monitored. [SSS177]

The TCS shall be capable of monitoring and displaying the signal strength of the received and transmitted signals for the selected data terminal. [SSS178]

The TCS shall be capable of monitoring and displaying the signal quality of the received and transmitted signals for the selected data terminal. [SSS179]

The TCS shall be capable of presenting to the operator a visual depiction of the minimum and maximum data link operational ranges. [SSS180]

## 3.2.3 Payload Product Management Function

The TCS will have the functionality necessary to manage all aspects of payload product handling to include receiving, processing, displaying, and performing limited exploitation. The payload product includes the payload sensor output and the appropriate AV and payload telemetry data.

## 3.2.3.1 Payload Product Processing Capability

The TCS shall have the functionality to process payload product data from Electro Optical (EO), Infrared (IR), and Synthetic Aperture Radar (SAR) payloads. [SSS182] This functionality, as a minimum, shall include: formatting, storing, internally routing, and recording the video [SSS190]; creating and storing a freeze frame of the video [SSS191]; retrieving and displaying the video [SSS192]; printing a hard copy of freeze frame video [SSS193]; and processing digital imagery for export and dissemination [SSS194]. Payload data includes the digital and analog imagery and associated telemetry sent to the TCS from each of these payloads.

The TCS shall be able to store up to 24 hours of payload data. [SSS184] External storage can be utilized for this purpose.

The TCS shall be in compliance with Common Imagery Ground Surface Station (CIGSS), United States Imagery Standards (USIS), Video Working Group Standards Architecture, National Imagery Transmission Format (NITF) Version 2.0, and Global Command Control Systems (GCCS) when processing payload imagery data. [SSS185]

The NITF 2.0 imagery files generated by the TCS shall contain the necessary telemetry and support data to permit subsequent imagery exploitation by C4I systems. [SSS186]

The TCS shall have a built-in text entry capability including the ability to annotate textual information on imagery. [SSS187]

The TCS shall be capable of receiving secondary HAE UAV payload imagery. [SSS188]

Payload telemetry data shall be available to support other TCS functions as required. [SSS189]

## 3.2.3.2 Payload Product Display Capability

The TCS shall display live and recorded imagery data, with as well as without annotation and overlay, upon operator request. [SSS195] Annotation includes operator generated comments as well as graphics which are superimposed on the imagery. Overlays consist of information obtained from external sources that is selected by the operator for presentation with the imagery.

The TCS shall provide the capability to simultaneously view imagery as well as data from more than one payload, when applicable. [SSS537]

The TCS operator shall be able to select the content of the overlay information. [SSS196]

The TCS shall have the capability to select and deselect several types of cross hairs (or other similar ICON) to identify a selected point on a target. [SSS197]

RS170A video and digital imagery shall be routed to TCS functions and displayed upon operator request. [SSS198]

## 3.2.3.3 Payload Product Exploitation Capability

The TCS shall have the functionality to conduct limited exploitation, to include voice and textual reporting for spot and mission objectives, on the payload product data. [SSS200] Limited exploitation, as a minimum, will include image enhancement and annotation.

The image enhancement capability shall include contrast, brightness, edge enhancement, and sharpness. [SSS201]

The TCS shall provide the capability to capture frozen-frames of imagery and store these frozen images for further review and processing. [SSS202]

The TCS shall have the capability to display Near-Real Time (NRT) imagery to include, as a minimum, date/time group, target location coordinates when the target is in the center of the field of view, north seeking arrow, and AV position and heading. [SSS203]

The TCS shall provide the capability to compute the range and bearing between two geographic positions located on the payload imagery display. [SSS560]

## 3.2.4 Targeting Function

The TCS will have the functionality to determine target coordinates, and estimate target coordinate accuracy.

The TCS shall support a target location function where the operator can request the current ground location of the payload field-of-view center. [SSS206]

## 3.2.4.1 Target Coordinate Development Capability

The TCS shall have the functionality to determine the location of items of interest within the payload field of view, and express these locations in coordinates acceptable for military applications. [SSS207]

## 3.2.4.2 Target Accuracy Estimation Capability

The TCS shall have the functionality to develop an estimate of the error in computed target coordinates,

and associate the error estimate with the appropriate target. [SSS208]

## 3.2.5 C4I System Interface Function

The TCS shall be capable of entering DII-COE compliant (C4I) networks. [SSS209] Network interoperability will include, but not be limited to:

Advanced Tomahawk Weapons Control Station (ATWCS)

Advanced Field Artillery Tactical Data System (AFATDS)

All Source Analysis System (ASAS)

Automated Target Hand-off System (ATHS)

Closed Circuit Television (CCTV)

Common Operational Modeling, Planning, and Simulation Strategy (COMPASS)

Contingency Airborne Reconnaissance System (CARS)

Enhanced Tactical Radar Correlator (ETRAC)

Guardrail Common Sensor/Aerial Common Sensor (ACS) Integrated Processing Facility (IPF)

Intelligence Analysis System (IAS)

Joint Deployable Intelligence Support System (JDISS)

Joint Maritime Command Information System (JMCIS)

Joint Service Imagery Processing System – Air Force (JSIPS-AF)

Joint Service Imagery Processing System - Navy (JSIPS-N)

Joint Surveillance Target Attack Radar System (JSTARS) Ground Station Module/Common Ground Station (GSM/CGS)

Modernized Imagery Exploitation System (MIES)

Service Specific Mission Planners

\- Army Mission Planning System (AMPS)

\- Air Force Mission Support System (AFMSS)

\- Tactical Aircraft Mission Planning System (TAMPS)

Tactical Exploitation Group (TEG)

Tactical Exploitation Systeme (TES)

Theater Battle Management Core System (TBMCS)

TROJAN Special Purpose Integrated Remote Intelligence Terminal (SPIRIT) II

The TCS shall have the functionality necessary to manage all aspects of C4I system interfaces to include receiving, processing, and transmitting tactical information to include but not limited to character based text messages, NITF 2.0 imagery files, and RS-170A video. [SSS210]

The TCS shall provide the functionality necessary to interface with various C4I systems in order to satisfy the operational requirements for: [SSS211]

1. Tasking TCS to plan and conduct a mission.

2. Presentation of payload product and target coordinates for export and dissemination.

3. Use of UAV obtained data (Non-real time tracks, tactical points and amplifying information) to provide a C4I system with information that may be used by C4I system operators, for transmission on tactical data communication links, and available to support engagement by appropriate weapons systems.

The TCS shall have the capability to interoperate with a data server to receive, extract, and push intelligence data. [SSS212]

The TCS shall have the capability to use cable to deliver live video imagery in multiple locations. [SSS213]

The TCS shall have the ability to interface with Service specific ground and airborne Ultra High Frequency (UHF), Very High Frequency (VHF), UHF/VHF, and High Frequency (HF) radios for digital message transmission while using the same radios for record traffic. [SSS214] Record traffic is defined as operational/voice communications.

Where applicable, TCS data burst messages shall comply with Variable Message Formats. [SSS215]

The TCS shall export and disseminate formatted NITF 2.0 files [SSS558], digital imagery (if applicable) [SSS218], RS-170A video (with as well as without overlay) [SSS219], and tactical communication messages [SSS220].

## 3.2.5.1 C4I Interface Control Capability

The TCS will have the capability to manage all operational C4I interfaces across all 5 levels of interaction.

## 3.2.5.1.1 C4I Digital Interface Control Capability

The TCS shall, as a minimum, have the functionality to provide the following control capabilities:

1. Send and receive tactical communication messages. [SSS222]

2. Send and receive annotated and un-annotated digital imagery. [SSS223]

3. Establish digital communication and when completed terminate communications to the C4I systems specified in Section 3.2.5 [SSS224].

4. Establish and when completed terminate digital communication to peripheral devices. [SSS225]

## 3.2.5.1.2 C4I Analog Interface Control Capability

The TCS shall, as a minimum, have the functionality to provide the following control capabilities:

1. Send and receive analog imagery in RS-170A format with as well as without overlay. [SSS226]

2. Establish and when completed terminate analog communication to C4I systems specified in Section 3.2.5. [SSS227]

3. Establish and when completed terminate analog communication to peripheral devices. [SSS228]

## 3.2.5.2 C4I Interface Data Processing Capability

The TCS will have the functionality to process received C4I messages and to prepare C4I messages for transmission. Processing will include formatting, storing, routing, and display.

## 3.2.5.2.1 C4I Digital Interface Data Processing Capability

The TCS shall, as a minimum, have the functionality to provide the following digital data processing capabilities:

1. Create Tactical Communications Messages to include United States Message Text Format (USMTF), Tactical Fire (TACFIRE), Over The Horizon Gold (OTH-Gold), and Intelligence and Electronic Warfare Character Oriented Message Catalog (IEWCOMCAT) For Transmission (specific message types will be identified in the all applicable TCS to C4I IDDs) [SSS230]

2. Review Incoming Tactical Communication Messages [SSS231]

3. Prepare Annotated as well as Un-annotated Digital Imagery For Transmission [SSS232]

4. Review Incoming Annotated as well as Un-annotated Digital Imagery [SSS233]

All digital messages received by the TCS shall be automatically checked for errors and corrected when possible. [SSS234]

All erroneous messages that cannot be corrected by TCS shall be flagged to the operator. [SSS235]

The TCS shall provide the capability to log all incoming and outgoing formatted tactical messages. [SSS236]

## 3.2.5.2.2 C4I Analog Interface Data Processing Capability

The TCS shall, as a minimum, have the functionality to provide the following analog data processing capabilities:

1. Prepare annotated as well as un-annotated analog imagery for transmission [SSS237]

2. Receive incoming annotated as well as un-annotated analog imagery [SSS238]

## 3.2.5.3 C4I Interface Monitoring Capability

The TCS shall have the functionality to monitor the status of all C4I interfaces, and display appropriate control information. [SSS239]

The TCS shall, as a minimum, have the functionality to provide the following data monitoring capabilities:

1. Display which C4I systems are supported and online during a mission [SSS240]

2. Monitor the status of all incoming and outgoing tactical communication messages [SSS241]

3. Review all tactical communication messages received and transmitted [SSS242]

4. View incoming and outgoing, annotated as well as un-annotated analog imagery [SSS243]

5. View incoming and outgoing, annotated as well as un-annotated digital imagery messages

[SSS244]

## 3.2.6 AV Maintenance Function

TCS shall be capable of executing AV maintenance software and displaying appropriate status results. [SSS245]

## 3.2.7 Payload Maintenance Function

TCS shall be capable of executing payload maintenance software and displaying appropriate status results. [SSS246]

## 3.2.8 Data Terminal Maintenance Function

TCS shall be capable of executing data terminal maintenance software and displaying appropriate status results. [SSS247]

## 3.2.9 Workstation and Peripheral Equipment Maintenance Function

TCS shall be capable of executing workstation and peripheral equipment maintenance software and displaying appropriate status results. [SSS248]

## 3.2.10 Fault Detection/Location Function

Fault Detection/Location (FD/L) to the Line Replaceable Unit (LRU) level shall be provided to indicate the readiness status of TCS, if inherent to the COTS hardware and software utilized. [SSS249]

As a minimum, TCS shall provide Startup FD/L for the operator workstation. [SSS250]

The TCS shall allow the operator to control and monitor the AV's FD/L, if required and provided by the Original Equipment Manufacturer (OEM) [SSS251]; Payload's FD/L, if required and provided by the Original Equipment Manufacturer (OEM) [SSS252]; and Data Link FD/L, if required and provided by the Original Equipment Manufacturer (OEM) [SSS253].

## 3.2.10.1 Startup FD/L

\*\*DELETED\*\* [SSS25405]

\*\*DELETED\*\* [SSS25506]

\*\*DELETED\*\* [SSS25607]

\*\*DELETED\*\* [SSS25708]

\*\*DELETED\*\* [SSS258]

\*\*DELETED\*\* [SSS259]

3.2.10.2 Periodic FD/L

\*\*DELETED\*\* [SSS260]

\*\*DELETED\*\* [SSS261]

\*\*DELETED\*\*. [SSS262]

\*\*DELETED\*\* [SSS263]

\*\*DELETED\*\*. [SSS264]

\*\*DELETED\*\* [SSS265]

\*\*DELETED\*\* [SSS267]

3.2.10.3 Extensive FD/L

\*\*DELETED\*\* [SSS268]

\*\*DELETED\*\*. [SSS269]

\*\*DELETED\*\* [SSS27019]

\*\*DELETED\*\* [SSS27120]

\*\*DELETED\*\* [SSS27221]

\*\*DELETED\*\* [SSS27322]

\*\*DELETED\*\* [SSS274]

\*\*DELETED\*\* [SSS275]

## 3.2.11 Software Upgrade Function

The TCS shall allow authorized operators to install software upgrades via CD-ROM as well as other media storage devices. [SSS276] The TCS shall restrict operator access to this capability via password protection. [SSS277]

The TCS shall provide the capability for Authorized Operators to modify all TCS programmable parameters. [SSS278] As a minimum, the TCS shall restrict Operator access to this capability via password protection. [SSS279]

The TCS shall be capable of importing National Imagery Mapping Agency (NIMA) Digital Terrain Elevation Data (DTED), Digital Feature Analysis Data (DFAD), Arc Digitized Raster Graphic and

scanned hard copy maps, via compact disk. [SSS280]

The TCS shall be capable of importing map information via operator procedure [SSS555] and shall be capable of incorporating vector format and Compressed ADRG (CADRG) maps. [SSS281]

## 3.2.12 Software Debug and Monitoring Function

The TCS shall allow an Authorized Operator to execute a software debug capability and view the resulting debug diagnostic information. [SSS282] As a minimum, the TCS will restrict Operator access to this capability via password protection. [SSS283]

## 3.3 System External Interface Requirements

The TCS will interface with external systems to conduct mission coordination and operations.

The TCS shall provide the capability to interface with equipment necessary to provide connectivity with standard DoD tactical (VHF, UHF, and UHF/VHF) radios, Mobile Subscriber Equipment, and military and commercial satellite communications equipment. [SSS285]

The TCS shall interface with external mission tasking systems (e.g., receive tasking orders, coordinate mission certification). [SSS286]

The TCS shall provide the system functionality necessary to interface with the data terminal. [SSS287]

The TCS shall provide the system functionality to allow interfacing with external systems via a local area network. [SSS288]

The TCS shall provide external interfaces to launch and recovery systems. [SSS289]

## 3.3.1 Interface Identification

3.3.1.1 TCS to C4I

Figure 3.3.1.1-1 illustrates the TCS to C4I interfaces.

![](images/a730597376dccd77ff1a74c32f2ff387b1f4bfea00aa50020cae3077bf455bba.jpg)  
Figure 3.3.1.1-1 TCS to C4I Interface Diagram

The TCS will be interoperable with C4I systems, as listed in Section 3.2.5 of this document. Table 3.3.1.1-1 shows the implementation schedule for C4I interfaces. This prioritization schema has been validated by a Joint Requirements Oversight Council (JROC) Memorandum.

Table 3.3.1.1-1 C4I Interface Integration Priority Schedule
<table><tr><td rowspan=1 colspan=1>FY 97</td><td rowspan=1 colspan=1>FY 98</td><td rowspan=1 colspan=1>FY 99</td><td rowspan=1 colspan=1>FY 00</td><td rowspan=1 colspan=1>FY 01</td></tr><tr><td rowspan=1 colspan=1>AFATDS</td><td rowspan=1 colspan=1>IAS</td><td rowspan=1 colspan=1>JSIPS</td><td rowspan=1 colspan=1>ATHS</td><td rowspan=1 colspan=1>TBMCS</td></tr><tr><td rowspan=1 colspan=1>ADOCS</td><td rowspan=1 colspan=1>JDISS</td><td rowspan=1 colspan=1>ATWCS</td><td rowspan=1 colspan=1>AFMSS</td><td rowspan=1 colspan=1>TES(MIES)</td></tr><tr><td rowspan=1 colspan=1>ASAS</td><td rowspan=1 colspan=1>TROJAN SPIRIT II</td><td rowspan=1 colspan=1>CARS</td><td rowspan=1 colspan=1>TAMPS</td><td rowspan=1 colspan=1>ACS IPF</td></tr><tr><td rowspan=1 colspan=1>JSTARS-CGS</td><td rowspan=1 colspan=1>ETRAC</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>AMPS</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>CCTV</td><td rowspan=1 colspan=1>JMCIS/GCCS-M</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>COMPASS</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>JSIPS-N</td><td rowspan=1 colspan=1>TEG</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>JMCIS</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr></table>

For external communications to C4I systems the TCS shall utilize the Universal Communication Processor as well as the Common Message Processor (CMP) Government Off The Shelf (GOTS) software capabilities of the DII/COE to communicate with C4I systems using Tactical Communication (TACOMM) messages. [SSS290] Details of the TACCOM messages and the associated C4I system will be defined in the applicable TCS to C4I IDDs.

## 3.3.1.1.1 TCS to ASAS

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with ASAS. [SSS291] The interface requirements and specifications will be defined in the TCS to ASAS IDD, TCS 201.

## 3.3.1.1.2 TCS to JSTARS GSM

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with JSTARS GSM. [SSS292] The interface requirements and specifications will be defined in the TCS to JSTARS IDD, TCS 209.

## 3.3.1.1.3 TCS to JMCIS

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with JMCIS. [SSS293] The interface requirements and specifications will be defined in the TCS to JMCIS IDD, TCS 214.

## 3.3.1.1.4 TCS to JSIPS-N

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with JSIPS-N. [SSS294] The interface requirements and specifications will be defined in the TCS to JSIPS-N IDD, TCS 210.

## 3.3.1.1.5 TCS to AFATDS

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with AFATDS. [SSS295] The interface requirements and specifications will be defined in the TCS to AFTADS IDD, TCS 200.

## 3.3.1.1.6 TCS to JSIPS-AF

The interface requirements and specifications will be defined in the TCS to JSIPS-AF IDD, TCS 211.

## 3.3.1.1.7 TCS to CARS

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with CARS. [SSS297] The interface requirements and specifications will be defined in the TCS to CARS IDD, TCS 217.

## 3.3.1.1.8 TCS to CCTV

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with CCTV. [SSS298] The interface requirements and specifications will be defined in the TCS to CCTV IDD, TCS 205.

## 1. TCS to Service Mission Planners

The TCS will provide the necessary hardware and software functionality to allow the TCS to integrate with Service Mission Planners. The Service Mission Planners will consist of AMPS, AFMSS, and TAMPS.

## 1. TCS to Army Mission Planning System

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with AMPS.[SSS563] The interface requirements and specifications will be defined in the TCS to AMPS IDD, TCS 235.

## 3.3.1.1.9.1 TCS to Air Force Mission Support System

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with AFMSS.[SSS564] The interface requirements and specifications will be defined in the TCS to AFMSS IDD, TCS 220.

## 3.3.1.1.9.2 TCS to Tactical Aircraft Mission Planning System

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with TAMPS.[SSS565] The interface requirements and specifications will be defined in the TCS to TAMPS IDD, TCS 219

## 2. TCS to GCS/ACS IPF

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with GCS/ACS IPF. [SSS300] The interface requirements and specifications will be defined in the TCS to GCS/ACS IPF IDD, TCS 215.

## 3. TCS to JDISS

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with JDISS. [SSS301] The interface requirements and specifications will be defined in the TCS to JDISS IDD, TCS 212.

## 3.3.1.1.12 TCS to TES

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with TES. [SSS302] The interface requirements and specifications will be defined in the TCS to TES IDD, TCS 236.

## 3.3.1.1.13 TCS to IAS

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with IAS. [SSS303] The interface requirements and specifications will be defined in the TCS to IAS IDD, TCS 206.

## 3.3.1.1.14 TCS to ATHS

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with ATHS. [SSS304] The interface requirements and specifications will be defined in the TCS ATHS IDD, TCS 208.

## 3.3.1.1.15 TCS to ATWCS

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with ATWCS. [SSS305] The interface requirements and specifications will be defined in TCS ATWCS IDD, TCS203

## 3.3.1.1.16 TCS to TROJAN SPIRIT II

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with Trojan Spirit II. [SSS306] The interface requirements and specifications will be defined in the TCS to TROJAN SPIRIT II IDD, TCS 213.

## 3.3.1.1.17 TCS to TBMCS

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with TBMCS. [SSS307] The interface requirements and specifications will be defined in TCS to TBMCS IDD, TCS 221.

## 3.3.1.1.18 TCS to MIES

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with MIES. [SSS308] The interface requirements and specifications will be defined in the TCS to MIES IDD, TCS 216.

## 3.3.1.1.19 TCS to ETRAC

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with ETRAC. [SSS309] The interface requirements and specifications will be defined in the TCS ETRAC IDD, TCS 218.

## 3.3.1.1.20 TCS to COMPASS

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with COMPASS. [SSS310] The interface requirements and specifications will be defined in TCS to

## 3.3.1.1.21 TCS to TEG

The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with TEG. [SSS311] The interface requirements and specifications will be defined in TCS to TEG IDD, TCS 207.

## 4. TCS to DT Control

Figure 3.3.1.2-1 illustrates the TCS to DT control interface.

![](images/863dc5dc08fea9100cfa6c8177233244ded6150152ac16be00bdc615ed155cbb.jpg)  
Figure 3.3.1.2-1 TCS to DT Control Interface Diagram

The TCS shall provide interfaces with the respective UAV program-provided data links for command and control and UAV data.. [SSS312]

The TCS shall have provisions for simultaneously supporting both of the following external interfaces: LOS data link, SATCOM data link. [SSS313]

Details of the TCS to DT interface will be defined in the TCS to Data Terminal IDD , TCS 242.

## 5. TCS to Printer

Figure 3.3.1.4-1 illustrates the TCS to Printer interface.

![](images/7e62ea07675a35198a2a143a37ffd388ed43c8a7b08bf1e01dec0da2a2c84b34.jpg)  
Figure 3.3.1.3-1 TCS to Printer Interface Diagram

The TCS shall provide an interface between the TCS and an external hard copy printer. [SSS314]

The TCS shall as a minimum, allow Operator(s) to print freeze-frame video, C4I Messages, Mission Plans, FD/L information, and current map display. [SSS315]

The TCS shall have the functionality to output digital message data and imagery to a hard copy printer.

Details of the Tactical Control System (TCS) to printer interface will be defined in the TCS to Printer IDD, TCS 255.

## 3.3.1.4 External Data Storage Systems

Figure 3.3.1.4-1 illustrates the TCS to External Storage Device interface.

![](images/bee6f51cb49f1e5a4a36f2762687c3db5b07c97ad3e3c172beb0563009fd20f5.jpg)  
Figure 3.3.1.4-1 TCS to External Data Storage System Interface Diagram  
The TCS shall provide an interface between the TCS and external data storage systems. [SSS317]

The TCS shall have the functionality to transfer digital data as well as digital imagery to and from external data storage systems. [SSS318]

Details of the Tactical Control System (TCS) to external data storage interface will be defined in the TCS to External Data Storage IDD, TCS256.

## 3.3.1.5 TCS to External Power

Figure 3.3.1.5-1 illustrates the TCS to External Power interface.

![](images/44117de578298eae107f3f0535af5170013c8c9f7520582bd380cc586bc2fa7a.jpg)  
Figure 3.3.1.5-1TCS to External Power Interface Diagram

The TCS shall have an interface between the TCS and DoD standard power supply equipment. [SSS319]

The TCS shall have the functionality to connect to the power supply equipment provided in the TCS operating environment. [SSS320]

Details of the Tactical Control System (TCS) to external power interface will be defined in the TCS to External Power IDD, TCS 257.

## 3.3.1.6 TCS to Geopositional Data

Figure 3.3.1.6-1 illustrates the TCS to Geopositional Data interface.  
![](images/2250a1593efa098d86baaf6d2723931a43a044bd8f97b9ddc644bb10616b8d24.jpg)  
Figure 3.3.1.6-1 TCS to Geopositional Data Interface Diagram

The TCS shall have an interface to a source of current navigation information. [SSS321] As a minimum this information will include the location of all data terminals, launch and recovery sites, and the controlling TCS.

Details of the Tactical Control System (TCS) to external power interface will be defined in the TCS to Geopositional Data IDD, TCS 243.

## 3.4 System Internal Interface Requirements

Figure 3.4-1 illustrates the TCS internal interfaces.

![](images/be720622a5cf444c0ac6ec70424505c1fc667c54ef3482d98f707a21a2448b5f.jpg)  
Figure 3.4-1 TCS Internal Interface Diagram

Except for the internal interfaces enumerated under this section, all TCS internal interfaces are left to the design and to the requirement specifications for system components.

The TCS will provide, as a minimum, the following internal interfaces:

1. AV Standard Interface.

2. Data Server

3. SAR Processor.

4. Intercom.

5. Local Printer.

6. Video Cassette Recorder

7. Storage devices.

8. Uninterruptible Power Supply

## 3.4.1 AV Standard Interface

The TCS shall implement an AV Standard Interface that will provide the proper data format to ensure communications with the selected AV. [SSS322] This interface shall allow for addition of future AVs and will provide the generic architecture to ensure interoperability. [SSS323]

The uplink and downlink information passed between the TCS and the AV shall be in accordance with the associated AV documentation. [SSS324]

The TCS shall support a concurrent uplink and downlink capability. [SSS325]

The AV Standard Interface requirements and specifications will be defined in the AV Standard IDD, TCS 229 .

The AV Standard Interface is designated as a mission and safety critical interface for the TCS.

## 3.4.2 Real Time Processor

The TCS shall provide an internal interface for establishing communications with the Real Time Processor (RTP) within TCS. [SSS326]

This interface shall allow the information from the data server to be made available to other components of the TCS. [SSS327]

The RTP interface shall support distributed processing capability. [SSS328]

The RTP interface requirements and specifications will be defined in the Data Server IDD, TCS 238.

## 3.4.2.1 Distributed Processing

Remotely hosted applications shall communicate in a client server relationship via the defined data server interface. [SSS329]

## 3.4.3 SAR Processor

The TCS shall provide an internal interface for the SAR Processor in order to disseminate SAR information (to include imagery and telemetry) to other components of the TCS. [SSS330]

The SAR Processor interface requirements and specifications will be defined in the TCS to SAR Processor IDD, TCS 240.

## 3.4.4 Intercom

The TCS shall incorporate an intercom system that provides verbal communicate in the situation where

there are multiple operators. [SSS331]

The intercom system shall be compatible with service specific voice communication systems. [SSS332]

The intercom interface requirements and specifications will be defined in the TCS to Intercom IDD, TCS 253.

## 3.4.5 VCR

The TCS will provide an interface between the TCS and a video cassette recorder.

The TCS shall allow the Operator(s) to fully control the VCR via the TCS Display input device(s). [SSS334]

The TCS shall be able to route VCR recorded payload video to the C4I Interfaces. [SSS335]

An RS-170A video interface shall be provided for the system to output and input analog imagery and overlays to and from a Video Cassette Recorder (VCR) for recording and playback. [SSS336]

Details of the VCR interface will be defined in the TCS to VCR IDD, TCS 246.

## 3.4.6 Printer

The TCS shall have ports for outputting data and imagery to an internal hard copy printer. [SSS337]

The TCS shall, as a minimum, allow the Operator(s) to print freeze-frame video, C4I Messages, Mission Plans, FD/L information, and current map display to an internal printer. [SSS338]

Details of the printer interface will be defined in the TCS to Printer IDD, TCS 255.

## 3.4.7 Data Storage Devices

The TCS shall be able to access data storage devices. [SSS339]

The TCS shall have the functionality to transfer digital data as well as digital imagery to and from data storage devices. [SSS340]

## 3.4.7.1 CD Drive

The TCS shall provide a CD drive for the retrieval of TCS data. [SSS341]

## 3.4.7.2 Tape Drive

The TCS shall provide a tape drive for storage and retrieval of TCS data. [SSS342]

## 3.4.7.3 Redundant Array Of Inexpensive Disks (RAID)

The TCS shall provide a RAID for storage and retrieval of TCS data, if required. [SSS343]

## 3.4.8 Uninterruptible Power

The TCS shall have an interface to an uninterruptible power supply. [SSS344]

## 6. System Internal Data Requirements

All TCS internal data decisions will be left to the design and the requirement specifications for system components.

## 3.6 Adaptation Requirements

This section not applicable, therefore tailored out.

## 3.7 Safety Requirements

The TCS design shall consider all safety requirements affecting design and performance except nuclear safety. [SSS345]

The TCS safety requirements are intended to eliminate as well as control potential hazards to equipment and personnel involved in the TCS. The TCS shall comply with para 5.3 of MIL-STD 882C, “System Safety Program Requirements”, dated 19 January 1993 w/ Notice 1 dated 19 January 1996. [SSS346]

## 3.7.1 Air Vehicle Safety

The TCS shall provide sufficient cues to allow the operator to safely take-off, land and navigate under Instrument Flight Rules. [SSS347]

The TCS shall provide adequate capability to allow the operator to operate each UAV within its certified operational flight envelope. [SSS348]

Appropriate cautions and warnings shall be provided to the operator if the air vehicle deviates into unsafe flight regime. [SSS349]

For mission planning, the TCS shall provide terrain avoidance warning and minimum reception altitude calculations for line of sight flights. [SSS350]

During mission execution, the TCS shall provide the operator a cautions and warnings when the UAV system has identified a malfunction. [SSS351]

The TCS shall provide the required information to allow the operator to maintain safe separation from other aircraft and a safe altitude in civilian airspace per Federal Aviation Administration (FAA) rules. [SSS352]

The TCS shall be designed such that no single hardware failure results in an unsafe command to be transmitted to the air vehicle. [SSS353]

The TCS shall be designed such that no single software error results in an unsafe command to be transmitted to the air vehicle. [SSS556]

The TCS shall be capable of restoring power in sufficient time to avoid loss of air vehicle control during power outages. [SSS354]

The TCS shall monitor the uplink and downlink to each UAV under its control. [SSS355]

Upon detection of loss of link, the TCS shall attempt to reestablish communications with the air vehicle. [SSS356]

## 3.7.2 Human Safety

The TCS design shall provide protection against injury to TCS operators and maintenance personnel. [SSS357] The system design shall use MIL-STD-2036, Section 5.1.3.11 as a guide, with regard to personnel hazards, and MIL-STD-1472D, Section 5.13, as a guide for safety from a human engineering viewpoint. [SSS358]

## 3.7.3 System Safety And Health Hazard Assets

System safety and health hazards, if any, shall be identified and evaluated during Phase I of the TCS development. [SSS359]

Risk levels and a program to manage the probability and severity of hazards shall also be developed. [SSS360]

## 3.8 Security And Privacy Requirements

The TCS is an Automated Information System (AIS). Therefore, as per DoD Regulation 5000.2-R, dated March 15, 1996, the TCS shall meet security requirements in accordance with DoD Directive 5200.28(D), “Security Requirements for Automated Information Systems” dated March 21, 1988. [SSS361]

The TCS shall be accredited by the Designated Approving Authority prior to processing classified as well as sensitive unclassified data. [SSS362]

## 3.8.1 Computer Security

Using risk assessment procedures defined in DoD 5200.28(D), a risk index and the minimum security requirements for TCS shall be determined. [SSS363] The inputs to this procedure are the clearance or authorization of the TCS users and the sensitivities of the data that the TCS processes, stores or transfers. These requirements pertain to the TCS computer hardware and software.

The TCS data sensitivities shall be determined by the data sensitivities of the systems with which it

interfaces, to including the air vehicles, payloads, and C4I systems. [SSS364]

## 3.8.2 Communications Security

Links that provide communications between the TCS and other systems shall be secured in a manner appropriate for the sensitivities of the material passed through such links, in accordance with DoD Directive C-5200.5, “Communication Security (COMSEC)” dated 21 April 1990. [SSS365]

## 3.8.3 Physical Security

The TCS shall be designed to protect its communication and data links against enemy Electronic Warfare (EW) threats, physical anti-radiation weaponry and physical destruction. [SSS366]

All hardware, software, documentation, and sensitive information processed by TCS shall be physically protected, minimally at the level determined by the risk index computed in Section 3.8.1, to prevent intentional as well as unintentional disclosure, destruction, and modification. [SSS367]

The TCS shall be approved for operation at the same level as the systems with which it interfaces. [SSS368]

## 3.8.4 Personnel Security

All TCS users, operators, maintainers and other personnel having access to TCS shall be cleared to the highest sensitivity of the data that the TCS processes, stores and transfers. [SSS369]

Additional local site procedures shall be developed to prevent the intentional or unintentional disclosure of sensitive information to unauthorized individuals. [SSS370]

A training program consisting of an initial security training and awareness briefing covering AIS security in general but also tailored to the TCS shall be developed. [SSS371]

## 3.8.5 Privacy Requirements

This section not applicable, therefore tailored out.

## 3.9 System Environment Requirements

The TCS shall be capable of operation within environments specified in the System/Subsystem Design Document for the land-based shelter and shipboard environments. [SSS372]

The TCS hardware shall be mounted as well as ruggedized to withstand inter and intra theater movement. [SSS373]

## 3.10 Resource Requirements

## 3.10.1 Hardware Requirements

The TCS hardware will provide the functionality and capability to receive, process, and disseminate video and telemetry data from the AV and payload; perform mission planning; monitor and control the payload; monitor and control the AV; and monitor and control the data links.

The hardware of the TCS shall be capable of being scaled as well as being modular to meet the varying needs of the Services. [SSS374]

The TCS hardware shall allow for long range communications from one TCS to another [SSS375], data storage expansion [SSS376], access to other computers to share in processing capability [SSS377], and multiple external peripherals [SSS378].

The TCS hardware shall support the data rate characteristics of the AV, data link and payload to ensure interoperability. [SSS379]

For each OUTRIDER system, the TCS shall provide full independent computer redundancy. [SSS380]

The TCS shall conform with the National Institute for Standard Technology (NIST) Federal Information Processing Standard (FIPS) Publication 151-2 (POSIX.1). [SSS381]

## 3.10.1.1 Performance

The TCS shall have sufficient throughput to support the processing requirements of the selected data link. [SSS382]

## 3.10.1.2 Mass Storage

To meet growth requirements, the TCS shall be capable of adding additional storage without major hardware reconfiguration. [SSS383]

The TCS computer system shall contain a CD-ROM drive that is compatible with National Imagery and Mapping Agency (NIMA), CD-ROM Digital Terrain Elevation Data (DTED), Digital Feature Analysis Data (DFAD), and embedded training media. [SSS384]

## 3.10.1.3 Power

The TCS shall use standard military worldwide 110/220 volt 50/60 hertz generators and commercial power sources. [SSS385]

The TCS shall use standard electrical power sources available within the DoD family of ground mobile, airborne, and shipboard electrical power sources. [SSS386]

The TCS shall be capable of restoring power in sufficient time to avoid loss of critical mission data and loss of air vehicle control during power outages. [SSS387]

The TCS shall have an uninterrupted power supply for critical phases (landing and takeoff as a minimum) of mission execution. [SSS388]

## 3.10.2 Hardware Resource Utilization Requirements

The TCS throughput shall not exceed 50% of the throughput capability delivered over any 10 second period [SSS389], and as an objective throughput shall not exceed 25% of throughput capability delivered over any 10 second period. [SSS390].

The TCS shall be capable of providing a 50% spare memory storage capacity over delivered storage used [SSS391]. As an objective a 75% spare memory storage capacity over storage used shall be provided. [SSS392]

## 3.10.3 Computer Software Requirements

The TCS software will provide the functionality and capability to receive, process, and disseminate video and telemetry data from the AV and payload; perform mission planning; monitor and control the payload; monitor and control the AV; and monitor and control the data links.

The TCS shall have software based on Defense Information Infrastructure/Common Operating Environment per Assistant Secretary of Defense for Command, Control, Communications, and Intelligence (ASD(C3I)) Joint Technical Architecture (JTA). [SSS393]

The TCS shall comply with the Assistant Secretary of Defense (C3I) Joint Technical Architecture (JTA). This includes, but is not limited to, the language, the computer, database, architecture, and interoperability. [SSS394]

The TCS shall provide an open software architecture to be capable of supporting additional CSCIs, CSCs, and CSUs for future AVs, future payloads, and payload capabilities (e.g. auto-search and automatic target tracking), and future Tactical UAVs. [SSS395]

The TCS core software shall be generically written to provide level one through level five interaction for both Outrider and Predator UAVs and establish the architecture for future tactical UAVs. [SSS396]

The TCS software shall provide the UAV operator with the necessary tools for computer related communications, mission tasking, mission planning, mission execution, data receipt, data processing, and data dissemination. [SSS397]

The TCS software shall be capable of being hosted on a variety of computer operating systems that are organic to the various Services. [SSS398]

TCS software shall provide a windows based graphic operator interface. [SSS399]

The TCS software shall be non-proprietary and have unlimited data rights. [SSS400]

The TCS’s operating system and executable software shall be re-programmable without hardware disassembly. [SSS401]

Training software shall be alterable without affecting the configuration of the operational software. [SSS402] Training software is the software that provides the computer based training functionality for the system operator.

The TCS software shall restrict the operator(s) from exercising levels of interaction not achievable by the system. [SSS403]

## 3.10.3.1 Display

The TCS software shall provide a high resolution, computer generated, graphical user interface that enables the UAV operator that is trained on one system to control different types of UAVs as well as UAV payloads with minimal additional training. [SSS404]

Each control console shall have, at a minimum, the capability to display the following four display windows: (1) display to provide aircraft position, TCS position, flight path, and a waypoint graphics in the foreground which are positioned in relation to a map displayed in the background, (2) display to provide aircraft flight data or payload data in the foreground, and downlinked video in the background. (3)A display to provide graphic presentations of downlinked telemetry data, and (4) display to present the interface menus for workstation software. [SSS405]

## 3.10.4 Computer Communication Requirements

The DII/COE UCP/CMP shall provide a consistent and common set of interfaces for United States Message Text Format (USMTF), Army Tactical Command Control System (ATCSS), and Field Artillery Tactical Data Systems (FATDS) message sets. [SSS406]

The TACCOM segment shall provide external interfaces for the communications media as indicated in Table 3.10.4-1: [SSS407]

Table 3.10.4-1 Communication Media and Associated Interface Document
<table><tr><td colspan="1" rowspan="1">Communication Media</td><td colspan="1" rowspan="1">Interface Document</td></tr><tr><td colspan="1" rowspan="1">RS-232</td><td colspan="1" rowspan="1">IEEE RS-232</td></tr><tr><td colspan="1" rowspan="1">RS-422</td><td colspan="1" rowspan="1">EIA RS-422</td></tr><tr><td colspan="1" rowspan="1">RS-170A</td><td colspan="1" rowspan="1">ISO-XXX</td></tr><tr><td colspan="1" rowspan="1">Wire line, 2-wire</td><td colspan="1" rowspan="1">MIL-C-49104</td></tr><tr><td colspan="1" rowspan="1">Wire line, 4-wire</td><td colspan="1" rowspan="1">MIL-C-55425</td></tr><tr><td colspan="1" rowspan="1">MSE (DNVT, DSVT)</td><td colspan="1" rowspan="1">ICD MSE-001</td></tr><tr><td colspan="1" rowspan="1">MSE TPN</td><td colspan="1" rowspan="1">MSE System Specification, AppendixSR45</td></tr><tr><td colspan="1" rowspan="1">SINCGARS</td><td colspan="1" rowspan="1">ACCS-A3-409-001</td></tr><tr><td colspan="1" rowspan="1">ANG/GYC-7</td><td colspan="1" rowspan="1">ICD-016, ICD-017, TIDP for MTS</td></tr><tr><td colspan="1" rowspan="1">IEEE 802.3/LAN</td><td colspan="1" rowspan="1">ISO/IS 8802/2, ISO/IS 8802/3</td></tr></table>

The TACCOM segment shall provide API’s for the transmission of imagery in National Imagery Transmission Formats 1.1a and 2.0 as per MILSTD-2500 and to be compatible with the Common Imagery Ground/Surface Station (CGIS) Guidelines. [SSS408]

## 3.11 System Quality Factors

## 3.11.1 Functionality

The TCS data latency shall not be greater than that present in the Predator ground control station or Outrider ground control station, whichever is smaller. [SSS409]

## 3.11.2 Reliability

The TCS reliability will be considered in every phase of the design and development process and shall achieve a system reliability (Mean Time Between Failures MTBF) equal to or greater than that which is specified in the Predator and Outrider ORDs. [SSS410]

## 3.11.3 Maintainability

The TCS maintainability will be considered in every phase of the design and development process and shall achieve a system maintainability (Mean Time To Repair MTTR) equal to or greater than that which is specified in the Predator and Outrider ORDs. [SSS411]

The Design features shall be included to: [SSS412]

1. minimize the number and frequency of required preventive maintenance actions based on performance requirements and lowest life cycle costs;

2. minimize the contribution to degradation of TCS equipment reliability as a consequence of performing either preventive as well as corrective maintenance;

3. enable the performance of all maintenance actions with safety and comparative ease by providing adequate access to all equipment components and minimizing the requirements for special tools and test equipment;

4. minimize the requirement for specially trained maintenance personnel;

5. improve system availability by the effective selection and incorporation of Built In Test Equipment (BITE);

6. allow removal and replacement of replaceable units without soldering and unsoldering.

## 3.11.4 Availability

The TCS equipment shall achieve an availability (A<sub>o</sub>), as defined below, equal to or greater than that which is specified in the Predator and Outrider ORDs. [SSS413]

$$
\mathrm { A _ { \mathrm { 0 } } = ( O T + S T ) / ( O T + S T + T P M + T C M + T A L D T ) }
$$

where: OT denotes Operate Time

ST denotes Standby Time

TPM denotes Total Preventative Maintenance

TCM denotes Total Corrective Maintenance

TALDT denotes Total Administrative and Logistic Downtime

## 3.11.5 Flexibility

The total, fully useable, addressable, physically present program instruction memory and data storage memory for each processor shall have at least 50% unused memory during the Normal Operations Mode over any 10 second period. [SSS414]

The processing speed of each processor shall be such that at least 50% of the throughput of each processor remains unused over all 10 second periods and at least 20% of the throughput of each processor remains unused over one second periods regardless of the system function performed. [SSS415]

The I/O channel reserve capability for each processor shall have at least a 50% reserve, addressable and useable, I/O channel capacity over any 10 second period. [SSS416]

TCS software flexibility and expandability shall be provided through use of the DII COE and through use of standardized software development practices. [SSS417]

## 3.11.6 Portability

Hardware and software shall be selected for use in the TCS with the goal of providing ease of future changes to the TCS elements. [SSS418] The object of portability for the TCS is to select or develop hardware which will readily host emerging software packages and software which will be as independent of host hardware as possible.

The selection of processors, interface cards for communication interfaces, disk drives, video, networking equipment, and all other hardware for use in the TCS shall be made according to standards for production of an open architecture. [SSS419]

The selection of operating system and programming language for use in the TCS shall be made according to standards for development of an open architecture. [SSS420]

## 3.11.7 Reusability

This section not applicable, therefore tailored out.

## 3.11.8 Testability

Testability shall be considered in the design and development of the TCS. [SSS421]

The system shall be functionally and physically partitioned to allow for efficient fault isolation. [SSS422]

Control over internal items and devices shall be provided for detecting and isolating internal faults. [SSS423]

Test points and data paths shall be defined to support efficient fault isolation. [SSS424]

## 3.11.9 Usability

This section not applicable, therefore tailored out.

## 3.12 Design And Construction Constraints

The TCS shall provide the common software architecture for TCS interaction with Predator, Outrider, and future Tactical UAVs. [SSS425]

In the selection of hardware design solutions to satisfy the requirements herein, Non-Developmental Items (NDI) (off-the-shelf equipment previously approved for service use) shall be chosen to the maximum practicable extent. [SSS426] If NDI that provides the desired functions can not be identified, then Commercial-Off-The-Shelf (COTS) hardware may be used.

During Phase 1, design and construction will be accomplished in accordance with commercial best practices unless otherwise required to meet a specific service operational environmental factor. Design and construction requirements for Phase 2 will be revised to reflect appropriate government approved sub-tier specifications controlling all aspects of electrical and electronic or mechanical designs for new or modified TCS equipment.

## 3.12.1 Documentation

System documentation shall be developed as part of the TCS program and will follow MIL-STD-498 for format. [SSS427]

The documentation developed shall contain sufficient level of detail to identify the functional, operational and design requirements of the TCS. [SSS428]

The documentation shall contain sufficient technical detail to define the hardware and software design implemented to satisfy the system requirements. [SSS429]

The TCS documentation shall include: [SSS430]

1) The TCS System/Subsystem Specification (SSS)

2) The TCS System/Subsystem Design Document (SSDD)

3) The TCS Software Requirements Specification (SRS) (1 for each CSCI)

4) The Software Design Document (SDD) (1 for each CSCI)

5) The TCS Hardware Design Document (HDD)

6) Interface Design Document (IDD) for all interfaces

7) TCS Version Description Document(s) (VDD)

## 3.12.2 Materials

TCS material factors shall be governed by the NDI, GFE and COTS specifications developed by the equipment manufacturers, where applicable. [SSS431]

## 3.12.3 Electromagnetic Radiation

During Phase 1, control techniques to minimize electromagnetic interference, emanation, and susceptibility shall be used in the design of TCS equipment. [SSS432] This control will be inherent in the design of the TCS and the electrical and electronic equipment components and assemblies thereof.

The susceptibility to coupling and the propagation of Electromagnetic Interference (EMI) will be minimized by component location, cable routing, and judicious use of shielding.

There shall be neither unacceptable response nor malfunction of any TCS and associated equipment due to EMI produced by any as well as all of the TCS and equipment associated with the TCS. [SSS434]

The TCS shall be compatible with the external electromagnetic environment that is typical of the service specific environment in the TCS will be operated. [SSS435] The specific electromagnetic environment values will be determined during Phase I of the TCS development.

The TCS design shall ensure that personnel, fuel, and ordinance are not exposed to electromagnetic radiation as a result of operating the TCS. [SSS436] The specific radiation hazard (RADHAZ) and HERO values will be determined during Phase I of the TCS development.

As TCS transitions into Phase 2, electromagnetic radiation safety and operation specifications will be invoked in the LRIP specification.

## 3.12.4 Software

Newly designed software shall be developed in accordance with a tailored MIL-STD-498. [SSS437]

Software written for other systems shall be used in TCS where it is determined that the existing software is

suitable for use within the TCS software. [SSS438]

A modular architecture shall be used by the TCS software in order to support future interoperability with multiple types of UAVs and payloads while maintaining consistent displays and user interfaces. [SSS439] Software components satisfying common planning and control functions will allow for vehicle specific components to be integrated in the future.

## 3.12.5 Hardware

TCS hardware flexibility and expansion shall be provided through use of GFE, NDI and COTS hardware designed to be upgraded and expanded. [SSS440]

## 3.12.6 Responsiveness

After emplacement at the operational site, the TCS shall be capable of planning and launching a mission within 1 hour of tasking. [SSS441] Required activities include 1) mission planning of a minimum 1 waypoint mission, 2) preparing 2 AVs for flight, 3) data terminal set-up, 4) safety equipment emplaced, 5) and a single AV launched.

## 3.12.7 Endurance

The TCS shall be capable of operating continuously in functional Operation Mode for a minimum of 72 hours. [SSS442]

## 3.13 Personnel-Related Requirements

## 3.13.1 Human Factors Engineering (HFE)

The TCS shall have ergonomically designed operator controls and displays for the $5 ^ { \mathrm { t h } }$ percentile female to $9 5 ^ { \mathrm { t h } }$ percentile male operator. [SSS443]

The controls shall allow the air vehicle and payload operators to perform mission control, mission monitoring, and mission updates and modifications while wearing cold weather clothing and in a Mission Oriented Protective Posture. [SSS444]

The TCS shall provide the operator a caution and warning diagnostic when the TCS system has identified a malfunction. [SSS445]

The TCS shall have monitor(s) that allow reading of displays under direct sunlight and low light level environments. [SSS446]

The TCS HCI shall be a Graphical User Interface (GUI) based on X-windows and Motif. [SSS447]

When performing a given task during mission execution, the operator shall be given appropriate warning messages from other concurrently-executing subsystem tasks. [SSS448]

TCS Warning messages shall be color coded and flashed based on mission criticality. The color codes and flash frequencies will follow MIL-STD 1472 guidelines. [SSS449]

The TCS operator shall be required to enter an acknowledgment prior to disabling the display of critical warning flags for any AV, Payload, ADT, GDT, and TCS faults. [SSS450]

A combination of visual and auditory outputs will be provided to alert the TCS operator to situations which may require operator response.

Visual alerts to the TCS operator shall be in the form of a displayed message box that has a display priority greater than other existing windows to ensure that it is viewable immediately by the operator. [SSS452] The position of the displayed message window shall be easily adjustable by the operator to ensure that important mission data is not obscured. [SSS453]

In addition to displayed alert messages to the TCS operator, auditory alerts to include tones shall also be provided. [SSS454] The volume of these auditory tones shall be adjustable by the operator via keyboard and trackball input to at least 20dB above the speech interference level at the operator’s ear. [SSS455]

All TCS warning messages and HCI actions shall be archived for later review. [SSS456]

All TCS operator inputs shall be error checked such that any erroneous operator entry will not cause current processing to terminate. [SSS457] The HCI shall prompt the operator for a valid input. [SSS458]

Display jitter and flicker shall not be perceptible by the operator. [SSS459]

The operational tasks to be performed concurrently by the operator during normal operation will be determined by appropriate task analysis and function allocation.

The TCS shall facilitate Human-Computer Interfaces (HCIs) that support operation of all system modes, functions, and capabilities. [SSS461]

The Human Computer Interface (HCI) shall be designed and implemented in accordance with the TCS HCI Specification, TCS 108.[SSS462]

The HCI shall provide redundancy in all operations, so that the loss of any one HCI input device does not prohibit operation of any TCS function. [SSS463]

The TCS shall provide the functionality to display all HCI elements on any available monitor on the TCS workstation. [SSS464]

The TCS shall be capable of displaying a window within a window format to include, as a minimum, displaying a video window overlaid on a map screen as well as a map screen overlaid on a video screen. [SSS465]

The TCS shall provide full complementary control operations from the keyset as well as the X/Y control device (e.g., trackball, mouse, joystick). [SSS466]

The TCS shall provide access to the DII Style Manager so that pointing device characteristics can be

## modified. [SSS467]

The shall provide the functionality to have a maximum delay time of 1 second from operator command to system acknowledgement and response.[SSS 559]

The TCS shall provide a capability for porting an off-the-shelf, complex control joystick with multiple toggle and multi-position switches as part of the TCS hardware suite. [SSS468]

The TCS shall use graphical representations to convey information, such as system status, C4I links, and AV-GDT links. [SSS469]

The TCS shall provide for multi-level information display tailoring by the operator. [SSS470]

The TCS shall provide automated TCS system information, control options, and logical & simple operator guidance and support for immediate and adaptive responding to crisis situations. [SSS471]

The TCS shall provide maximum automated system software support to system status monitoring and alerting of the TCS operator when a preset system parameter goes under as well as over a set threshold. [SSS472]

The TCS shall provide the necessary processing, display, and control capabilities to ensure dynamic situational awareness input to the TCS operator. [SSS473]

The TCS shall minimize alphanumeric data display in favor of graphic, pictorial information display [SSS474]

The TCS HCI shall provide unambiguous AV and payload control and status feedback indicators to ensure safe, efficient operations of two AVs and their payloads by a single TCS station. [SSS475]

The TCS shall provide for a specific icon shape on a constant contrast background, as well as other visual information coding mechanisms, to cue the TCS operator regarding which UAVs are under his or her primary control. [SSS476]

The TCS HCI shall provide the capability to select and amplify an object and point on a map as well as payload screen. [SSS477]

The TCS HCI shall provide coarse and fine payload control capabilities directly on the payload screen. [SSS478]

The TCS HCI shall display the SAR imaging swath on the map display. [SSS479] The TCS HCI shall provide the on-screen capability to select and efficiently move as well as reorient a previously defined SAR imaging swath. [SSS480]

The TCS HCI shall provide the capability to lock onto and hold a coordinate point on the payload imagery window. [SSS481]

The TCS HCI shall provide the capability to display operator definable “Lock Out” zones around waypoints, Launch and Recovery Point (LRP), as well as any selected point on the AV flight path.

## [SSS482]

The TCS HCI shall provide for a rapid means to cancel aural warnings. [SSS484]

The TCS HCI shall provide for separation, grouping, and visual coding of multiple categories of alerts, to include Warnings, Cautions, and Advisories. [SSS485]

The TCS HCI shall provide for visual Warnings, Cautions, and Advisories to be displayed at or near the center of the field of view, i.e., within a 30<sup>o</sup> cone, of all monitors in a TCS system. [SSS486]

For AV safety as well as mission-critical Warnings, the TCS HCI shall provide a default selection as well as an override option, along with a selection of adaptive responses, and the minimum information necessary to assist the operator in responding quickly and adaptively to the emergency. [SSS487]

The TCS HCI shall provide for on-screen information to include, as a minimum, overlays, headers, cursors, alphanumeric annotation, waypoints, crosshairs, designed to be visible against the complete spectrum of map and payload video backgrounds. [SSS488]

The TCS HCI shall provide continuously-available, on-screen control functions for time and missioncritical operations, to include as a minimum print, freeze, declassification, mark VCR, declutter, cease RF transmission. [SSS489]

The TCS HCI shall provide for the capability to automatically designate target locations from the payload screen onto the map screen. [SSS490]

## 3.14 Training Related Requirements

Formal training programs shall not be required for TCS Phase 1, Program definition and Risk Reduction. Trained and proficient personnel from the Original Equipment Manufacturers, Government Engineering Teams, supporting Contractors, and Military Personnel will support the operation and maintenance of the demonstration system equipment throughout Phase 1.

TCS training and training support shall include the processes, procedures, techniques, training devices and equipment to train civilian, active duty and reserve military personnel to operate and support the TCS system. [SSS491] This will include: individual and crew training; new equipment training; initial, formal, and on-the-job training. TCS training will strike a balance between institutional, new equipment and unit training.

The TCS system shall provide, for the operator and maintainer, an embedded or add-on interactive training courseware with self-paced instruction, duplicating UAV flight performance characteristics, capabilities, and limitations. [SSS492] The OUTRIDER TCS system shall be compatible with the U.S. Army Intelligence and Electronic Warfare Tactical Proficiency Trainer as an objective. [SSS493]

The interactive courseware training capability for TCS shall be developed during Phase I and introduced to the user during scheduled demonstrations and tests. [SSS494]

The training capability for performance of TCS functions shall include primary mission (flight route/payload) planning, mission control and monitoring, imagery processing, tactical communications, AV control communications and TCS system on line diagnostics. [SSS495] This capability will be qualified and improved during Phase I based upon use and feedback from qualified operators and users demonstrating TCS system equipment throughout Phase I. Instructional support materials and training courseware for classroom discussion and lecture will be developed to support institutional, new equipment training and unit training.

The TCS shall provide the functional capability to train in the operation of the TCS system, performance of TCS UAV functions, and on line system troubleshooting. [SSS496]

TCS system training shall include system architecture, component familiarization, and system startup, initialization, system recovery and shutdown. [SSS497]

The TCS system shall not support formal Training operations concurrent with the execution of an actual mission. [SSS499] The capability for the conduct of actual communications processing concurrently with Training operations shall be provided if and only if messages are identified as training messages. [SSS500]

Training shall be adequate to maintain operator and maintainer skills and proficiencies. [SSS501]

TCS shall record operator and maintainer actions for self assessment and performance enhancement. [SSS502]

Operator and maintainer performance shall be measurable using parameters retrievable from the TCS to determine proficiency levels. [SSS503]

## 3.15 Logistics-Related Requirements

During Phase 1, TCS logistic support requirements will be based on known and predicted failure rates of components, and the criticality of those elements to the system development and flight test processes. Logistic requirements for Phase 2 will be determined and incorporated into LRIP requirements and specifications.

Support for the TCS shall be in accordance with the Integrated Logistical Support Plan (ILSP) and the maintenance concepts and policies of the individual Services. [SSS504]

All TCS Operator Manuals and Technical Manuals shall be verified and validated prior to initial operational test. [SSS529]

TCS transport and storage containers shall be reusable and enable the operators to set-up equipment within the established timelines in their ORDs. [SSS505]

The TCS shall adhere to DoD regulations and policy governing military standards for logistics, Petroleum, Oil and Lubricants (POL), Test, Measurement, and Diagnostic Equipment (TMDE), tools, and other support items. [SSS506]

Standard tools, TMDE, repair parts, and lubricants shall be used to maintain the TCS. Exceptions shall be considered on a case by case basis. [SSS507]

Each Service shall support the TCS as part of the UAV system which is organic to them. [SSS508]

The TCS shall be maintained in accordance with the UAV ORD for that Service and the level of repair analysis for the hardware chosen. [SSS509]

A TCS support and fielding package shall be developed and available for operational testing. [SSS510]

The TCS shall be maintained in accordance with Services’ approved UAV maintenance concepts and procedures. [SSS511]

To the maximum extent possible, general purpose test equipment (GPTE) and common tools resident in each service shall be used to perform all corrective and preventative maintenance at all authorized levels of maintenance. [SSS512]

Tools and test equipment required to maintain the TCS but not resident in each service inventory shall be identified as special tools and special purpose test equipment (SPTE), respectively, and kept to a minimum. [SSS513]

The environmental support required by the TCS shall be at least the same as that required for the respective UAV System. [SSS514]

Basing for the system will follow the plan for UAV units and service command echelon requirements as delineated in the ORD. [SSS515]

## 3.15.1 Transportability

The TCS shall meet the deployment criteria for the organic unit to which it is assigned. [SSS516]

The TCS shall be transported into the theater as an organic component of the operational UAV system being deployed. [SSS517]

TCS transportation in theater for Army and Marine Corps systems shall be by ground, air, as well as rail transportable. [SSS518]

For the Air Force, TCS transportation to the theater shall be by air. [SSS519] Within the theater, the USAF GCS shall be capable of being moved around an established air field. [SSS520]

## 3.15.1.1 Ground

The TCS shall be ground transportable. [SSS521]

## 3.15.1.2 Air

The TCS shall be air transportable by helicopter (CH-47/CH-53D) and C-130 drive-on/drive-off capable. [SSS522]

## 3.15.1.3 Sea

The TCS shall be sea transportable. [SSS523]

## 3.15.1.4 Rail

The TCS shall be rail transportable. [SSS524]

## 3.15.1.5 Preparation Time

The TCS shall be configurable for sea, ground, as well as air transport in 2 hours or less. [SSS525]

The TCS system shall be capable of being de-configured from sea, ground, as well as air transport and ground-mobile in 2 hours or less. [SSS526]

## 3.16 Other Requirements

The TCS shall have an objective capability to be integrated and operated from tactical and command and control aircraft. [SSS531]

The TCS shall have an objective capability to be integrated and operated from submarines. [SSS532]

The TCS shall have a capability to be integrated and operated from land based platforms. [SSS533]

The TCS shall have an objective capability to be integrated and operated from ships. [SSS534]

## 3.17 Packaging Requirements

This section not applicable, therefore tailored out.

## 3.18 Precedence And Criticality Of Requirements

All requirements in this specification are of equal weight and criticality unless otherwise identified in the traceability Table in Appendix A.

When the requirements of the Operational Requirement Document (ORD), this System/Subsystem Specification (SSS), other related requirement documents, and referenced documents are in conflict, the following precedence will apply:

7. TCS ORD – The ORD shall have precedence over any other TCS documentation.

8. TCS SSS – This SSS shall have precedence over other requirements documents except item (1.) above.

9. Other TCS requirement documents – Other requirement documents shall have precedence over any referenced documents.

10. Referenced documents – Documents referenced herein and in other TCS requirement documents shall have precedence over all applicable subsidiary documents referenced therein.

In the event of conflicting requirements within a TCS requirement document, the requirements shall be traced to the next higher precedence requirement document for clarification. If further resolution is required, the developer will notify the procuring agency.

# 11.QUALITY ASSURANCE PROVISIONS

## 12.Responsibility for Inspections.

The Quality Assurance (QA) Program is an integral part of the development process for the TCS , whereby all phases of the development of a system must be inspected and tested, as these phases occur. The objectives and processes of the QA Program applicable to this development effort are contained in the TCS Integration Program Quality Assurance Plan, NSWCDD/TR-96/XXX.

## 13.Special Tests and Examinations.

Verification of requirements will be accomplished by the use of appropriate combinations of inspections, analyses, demonstrations and tests. The method to be used for verification of each requirement is identified in Appendix B. The following defines verification methods as used in this specification:

14. Demonstration: The operation of the system, or a part of the system, that relies on observable functional operation not requiring the use of instrumentation, special test equipment, or subsequent analysis.

15. Test: The operation of the system, or a part of the system, using instrumentation or other special test equipment to collect data for later analysis.

16. Analysis: The processing of accumulated data obtained from other qualification methods. Examples are reduction, interpolation, or extrapolation of test results.

17. Inspection: The visual examination of system components, documentation, etc.

18. Special qualification methods. Any special qualification methods for the system, such as special tools, techniques, procedures, facilities, acceptance limits, use of standard samples, pre-production or periodic production samples, pilot models, or pilot lots.

## 19. Government Verification.

All QA functions performed will be monitored by the QA Team. Verification will consist of surveillance of the operation to determine that practices, methods, and procedures are being properly applied; product inspection to measure quality of products to be offered for acceptance; and product inspection of delivered products to ensure compliance with all the requirements of this specification.

## 20. Integrated Test Program.

The system will be tested via an integrated program conducted according to the TCS Master Test Plan, NSWCDD/TR-96/XXX. The integrated program consists of three (3) distinct categories, as defined in the Master Test Plan: data link tests, integration tests, and flight tests.

## 21. Requirements Cross Reference.

Requirements within this document represent a tailored use of MIL-STD-498. Verification and testing, per Section 4.2, of the system for compliance with the requirements specified herein will be accomplished per the cross-reference tables in Appendix B.

## APPENDIX A: Requirements Traceability Matrix

## TCS ORD TO TCS SSS REQUIREMENT CROSS-REFERENCE MATRIX

<table><tr><td colspan="1" rowspan="1">ORDNUMBER</td><td colspan="1" rowspan="1">ORD REOUIREMENT</td><td colspan="1" rowspan="1">SSS REOIREMENT AND NUMBER</td></tr><tr><td colspan="1" rowspan="1">ORD001</td><td colspan="1" rowspan="1">The TCS shall have the capability to be configured and down-scaled to meet the user'sdeployability or operator limitations.</td><td colspan="1" rowspan="1">SSS440TCS hardware flexibility and expansion shall be provided through use of GFE, NDI and COTShardware designed to be upgraded and expanded.</td></tr><tr><td colspan="1" rowspan="1">ORD002</td><td colspan="1" rowspan="1">The TCS software shall provide a high resolution, computer generated, graphics user interface thatenables the UAV operator that is trained on one system to control different types of UAVs or UAVpayloads with minimal additional training</td><td colspan="1" rowspan="1">SSS404The TCS software shall provide a high resolution, computer generated, graphical user interface thatenables the UAV operator that is trained on one system to control different types of UAVs or UAVpayloads with minimal additional training.</td></tr><tr><td colspan="1" rowspan="1">ORD003</td><td colspan="1" rowspan="1">The TCS software shall have an open architecture and be capable of being hosted on computersthat are typically supported by the using Service</td><td colspan="1" rowspan="1">SSS398The TCS software shall be capable of being hosted on a variety of computer operating systems thatare organic to the various Services.SSS419The selection of processors, interface cards for communication interfaces, disk drives, video,networking equipment, and all other hardware for use in the TCS shall be made according tostandards for production of an open architecture.SSS420The selection of operating system and programming language for use in the TCS shall be madeaccording to standards for development of an open architecture.SSS438Software written for other systems shall be used in TCS where it is determined that the existingsoftware is suitable for use within the TCS software</td></tr><tr><td colspan="1" rowspan="1">ORD004</td><td colspan="1" rowspan="1">The TCS software shall be Defense Information Infrastructure/Common Operating Environmentcompliant.</td><td colspan="1" rowspan="1">SSS417TCS software flexibility and expandability shall be provided through use of the DII COE andthrough use of standardized software development practices.</td></tr><tr><td colspan="1" rowspan="1">ORD005</td><td colspan="1" rowspan="1">The TCS software shall be non-proprietary.</td><td colspan="1" rowspan="1">SSS400The TCS software shall be non-proprietary.</td></tr><tr><td colspan="1" rowspan="1">ORD006</td><td colspan="1" rowspan="1">For the U.S. Army and the U.S. Marine Corps, the TCS shall be an integral part of the TUAV twoHMMWV-based GCSs</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">ORD007</td><td colspan="1" rowspan="1">The TCS hardware shall allow for long range communications from one TCS to another</td><td colspan="1" rowspan="1">SSS375The TCS hardware shall allow for long range communications from one TCS to another.</td></tr><tr><td colspan="1" rowspan="1">ORD008</td><td colspan="1" rowspan="1">The TCS hardware shall allow for data storage expansion</td><td colspan="1" rowspan="1">SSS376The TCS hardware shall allow for data storage expansion</td></tr><tr><td colspan="1" rowspan="1">ORD009</td><td colspan="1" rowspan="1">The TCS hardware shall allow for access to other computers to share in processing capability.</td><td colspan="1" rowspan="1">SSS377The TCS hardware shall allow access to other computers to share in processing capability</td></tr><tr><td colspan="1" rowspan="1">ORD010</td><td colspan="1" rowspan="1">The TCS hardware shall allow for multiple external peripherals</td><td colspan="1" rowspan="1">SSS378The TCS hardware shall allow for multiple external peripherals.</td></tr><tr><td>ORD011 25. landing</td><td>The TCS shall support 5 levels of UAV interaction: 22. Level one is the receipt and transmission of secondary imagery and/or data 23. Level two is the direct receipt of imagery and/or data 24. Level three is the control of the UAV payload in addition to direct receipt of imagery/data Level four is control of the UAV, less launch and recovery, plus all the functions of level three 5. Level five is the capability to have full function and control of the UAV from takeoff to</td><td>SSS409 The TCS data latency shall not be greater than that present in the Predator ground control station or Outrider ground control station, whichever is smaller. SSS329 Remotely hosted applications shall communicate in a client server relationship via the defined data</td></tr><tr><td rowspan="8"></td><td rowspan="8"></td><td>server interface. SSS328</td></tr><tr><td>The RTP interface shall support distributed processing capability. SSS327</td></tr><tr><td>This interface shall allow the information from the data server to be made available to other components of the TCS.</td></tr><tr><td>SSS326 The TCS shall provide an internal interface for establishing communications with the RTP within TCS.</td></tr><tr><td>SSS175 The TCS shall be capable of automatically controlling the transmitter and receiver frequencies of the selected data terminal.</td></tr><tr><td>SSS173 The TCS shall be capable of automatically controlling the transmitter and receiver modes of the selected data terminal. SSS172</td></tr><tr><td>The operator shall be able to manually override the automatic function selection if desired. SSS171 The TCS shall be capable of automatically controlling the transmitter and receiver functions of the</td></tr><tr><td>selected data terminal. SSS170</td></tr><tr><td rowspan="4"></td><td>The TCS shall be capable of properly selecting and positioning antennas to maintain line-of-sight or satellite communication.</td></tr><tr><td>SSS167 The TCS shall provide automatic pointing commands for directional antennas</td></tr><tr><td>SSS557 The TCS shall incorporate antenna pedestal 3 -axis stabilization to compensate for platform (e.g.</td></tr><tr><td>64 SSS165 The TCS shall provide an interactive display for the purpose of controlling the data link terminal.</td></tr><tr><td rowspan="4"></td><td>ship, or HMMWV) motion, if applicable.</td></tr><tr><td>SSS164</td></tr><tr><td>The TCS shall support a sequential LOS data link and beyond LOS data link capability.</td></tr><tr><td></td></tr></table>

TCS Block 0 Version 2.0
<table><tr><td>ORD012</td><td>The TCS shall provide full interoperability between the Services and their UAV systems with varying levels of UAV interaction.</td><td>SSS009 The TCS system shall provide software capabilities and hardware configurations necessary to fulfill the operational tasking requirements across the 5 levels of interaction.</td></tr><tr><td>ORD013</td><td>The TCS core software shall be generically written to provide Level Five interaction for both TUAV and MAE UAVs and establish the architecture for future tactical UAVs.</td><td>SSS396 The TCS core software shall be generically written to provide level one through level five interaction for both Outrider and Predator UAVs and establish the architecture for future tactical UAVs. SSS437</td></tr><tr><td>ORD014</td><td>The TCS software and software related hardware shall be developed so that it is scaleable to meet the users&#x27; needs.</td><td>Newly designed software shall be developed in accordance with a tailored MIL-STD-498. SSS004 The TCS shall consist of the TCS workstation Hardware Configuration Items (HWCIs), TCS Software Compute Software Configuration Items (CSCIs), and additional TCS Support HWCIs and</td></tr><tr><td rowspan="4">ORD015</td><td rowspan="4">The TCS shall prevent users from entering levels of interaction for which they are not authorized by software and/or hardware configuration.</td><td>CSCIs. SSS403 The TCS software shall restrict the operator(s) from exercising levels of interaction not achievable</td></tr><tr><td>by the system. SSS023 The TCS shall inform the operator if the operator attempts to execute a function that is prohibited</td></tr><tr><td>based upon the determined level of interaction. SSS022 Levels of interaction higher than that achievable by a particular TCS configuration shall be</td></tr><tr><td>prohibited. SSS021 During startup, the TCS shall determine which of the 5 levels of interaction are achievable by the TCS configuration being used.</td></tr></table>

<table><tr><td>SSS500 The capability for the conduct of actual communications processing concurrently with Training</td></tr><tr><td>operations shall be provided if and only if messages are identified as training messages. SSS047</td></tr><tr><td>Shutdown of the TCS shall include proper termination of all active interfaces.</td></tr><tr><td>SSS046</td></tr><tr><td>Shutdown of the TCS shall include shutdown of HCIs.</td></tr><tr><td>SSS045</td></tr><tr><td>Shutdown of the TCS shall include shutdown of appropriate functions.</td></tr><tr><td>SSS028</td></tr><tr><td>Initialization of the TCS shall include establishment of the state of readiness of all interfaces.</td></tr><tr><td>SSS027 Initialization of the TCS shall include start of HCIs.</td></tr><tr><td>SSS026</td></tr><tr><td>Initialization of the TCS shall include download of software.</td></tr><tr><td>SSS542</td></tr><tr><td>Initialization of the TCS HWCIs shall include startup of HWCIs.</td></tr><tr><td>SSS335</td></tr><tr><td>The TCS shall be able to route VCR recorded payload video to the C4I Interfaces.</td></tr><tr><td>SSS332</td></tr><tr><td>The intercom system shall be compatible with service specific voice communication systems.</td></tr><tr><td>SSS331 The TCS shall incorporate an intercom system that allows the operator(s) of the TCS to verbally</td></tr><tr><td>communicate with each other.</td></tr><tr><td>SSS210 The TCS shall have the functionality necessary to manage all aspects of C4I system interfaces to</td></tr><tr><td>include receiving, processing, and transmitting tactical information to include but not limited to character based text messages, NITF 2.0 imagery files, and RS-170A video.</td></tr><tr><td>SSS208</td></tr><tr><td>The TCS shall have the functionality to develop an estimate of the error in computed target coordinates, and associate the error estimate with the appropriate target.</td></tr><tr><td>SSS189</td></tr><tr><td>Payload telemetry data shall be available to support other TCS functions as required.</td></tr><tr><td></td></tr><tr><td>SSS180 The TCS shall be capable of presenting to the operator a visual depiction of the minimum and</td></tr></table>

<table><tr><td rowspan=1 colspan=1>ORD017</td><td rowspan=1 colspan=1>The TCS shall provide an open software architecture that can support future UAVs.</td><td rowspan=1 colspan=1>SSS395The TCS shall provide an open software architecture to be capable of supporting additional CSCIs,CSCs, and CSUs for future AVs, future payloads, and payload capabilities (e.g. auto-search andautomatic target tracking), and future Tactical UAVs.</td></tr><tr><td rowspan=1 colspan=1>ORD018</td><td rowspan=1 colspan=1>The TCS shall have software based on Defense Information Infrastructure/Common OperatingEnvironment per Assistant Secretary of Defense for Command, Control, Communications, andIntelligence (ASD(C3I)) Joint Technical Architecture (JTA)</td><td rowspan=1 colspan=1>SSS393The TCS shall have software based on Defense Information Infrastructure/Common OperatingEnvironment per Assistant Secretary of Defense for Command, Control, Communications, andIntelligence (ASD(C3I)) Joint Technical Architecture (JTA).</td></tr></table>

<table><tr><td>SSS490 The TCS HCI shall provide for the capability to automatically designate target transmissions from</td></tr><tr><td>the payload screen onto the map screen.</td></tr><tr><td>SSS489 The TCS HCI shall provide continuously-available, on-screen control functions for time and mission-critical operations, to include as a minimum print, freeze, declassification, mark VCR, declutter, cease RF transmission.</td></tr><tr><td>SSS488 The TCS HCI shall provide for on-screen information to include, as a minimum, overlays, headers, cursors, alphanumeric annotation, waypoints, crosshairs, designed to be visible against the complete</td></tr><tr><td>spectrum of map and payload video backgrounds. SSS487 For AV safety or mission-critical Warnings, the TCS HCI shall provide a default selection as well as</td></tr><tr><td>an override option, along with a selection of adaptive responses, and the minimum information necessary to assist the operator in responding quickly and adaptively to the emergency. SSS486</td></tr><tr><td>The TCS HCI shall provide for visual Cautions and Advisories to be displayed at or near the center of the field of view, i.e., within a 30o cone, of all monitors in a TCS system. SSS485</td></tr><tr><td>The TCS HCI shall provide for separation, grouping, and visual coding of multiple categories of alerts, to include Warnings, Cautions, and Advisories. SSS484</td></tr><tr><td>The TCS HCI shall provide for a rapid means to cancel aural warnings. SSS482</td></tr><tr><td>The TCS HCI shall provide the capability to display operator definable “Lock Out&quot; zones around waypoints, Launch and Recovery Point (LRP), or any selected point on the AV flight path.</td></tr><tr><td>SSS481 The TCS HCI shall provide the capability to lock onto and hold a coordinate point on-screen. SSS480</td></tr><tr><td>The TCS HCI shall provide the on-screen capability to select and efficiently move or reorient a previously defined SAR imaging swath.</td></tr><tr><td>SSS479 The TCS HCI shall display the SAR imaging swath on the map display. SSS478</td></tr><tr><td>The TCS HCI shall provide coarse and fine payload control capabilities directly on the payload screen.</td></tr><tr><td>SSS477 The TCS HCI shall provide the capability to select and amplify an object or point on a map or</td></tr></table>

<table><tr><td colspan="1" rowspan="1">ORD020</td><td colspan="1" rowspan="1">The TCS shall have monitor(s) that provide easy reading of displays</td><td colspan="2" rowspan="1">SSS446The TCS shall have monitor(s) that provide easy reading of displays under direct sunlight and lowlight level environments.SSS459Display jitter and flicker shall not be detectable by the operator.</td></tr><tr><td colspan="1" rowspan="1">ORD021</td><td colspan="1" rowspan="1">The TCS HCI shall be menu driven and have displays in a X-windows motif</td><td colspan="2" rowspan="1">SSS447The TCS HCI shall be a Graphical User Interface (GUI) based on X-windows and Motif.SSS399TCS software shall provide a windows based graphic operator interface.</td></tr><tr><td colspan="1" rowspan="1">ORD022</td><td colspan="1" rowspan="1">The TCS shall have peripheral ports to drive external devices. As a minimum, ports required willbe for monitor displays, mouse (or pointer device), keyboard, printer, LAN, EIA-RS-170, andexternal disk drives (if required)</td><td colspan="2" rowspan="1">SSS343The TCS shall provide a RAID for storage and retrieval of TCS data, if requiredSSS342The TCS shall provide a tape drive for storage and retrieval of TCS data.</td></tr><tr><td colspan="1" rowspan="1">ORD023</td><td colspan="1" rowspan="1">The TCS shall be capable of supporting additional software modules for future payloads, payloadcapabilities (e.g. autosearch and automatic target tracking), and future Tactical UAVs.</td><td colspan="2" rowspan="1">SSS439A modular architecture shall be used by the TCS software in order to support future interoperabilitywith multiple types of UAVs and payloads while maintaining consistent displays and user interfaces.Software components satisfying common planning and control functions will allow for vehiclespecific components to be integrated in the future.</td></tr><tr><td colspan="1" rowspan="1">ORD024</td><td colspan="1" rowspan="1">The TCS shall allow operators to have simultaneous flight and payload control of at least two airvehicles, beyond line of sight, using one TCS.</td><td colspan="2" rowspan="1">SSS125The TCS shall provide the necessary system capabilities required for AV flight control BLOS viauplink command to two MAE air vehicles.SSS124The TCS shall allow the operator to control an AV using the LOS or SATCOM data links.SSS149The TCS shall provide the necessary system capabilities required for payload control beyond line ofsight via uplink command of two air vehicles of the same type using sequential communicationtechniques. Sequential communication means alternatively communicating with one air vehicle andthen the other. Current air vehicle design does not permit concurrent communications with two airvehicles at the same time.</td></tr><tr><td colspan="3">TCS Block 0 TCS 102 Version 2.0 2/12/99</td></tr><tr><td colspan="3" rowspan="3">ORD025 The TCS shall be capable of being interoperable with different types of UAVs and UAV payloads across the 5 levels of UAV interaction.</td></tr><tr><td>levels of UAV interaction. SSS012</td></tr><tr><td>The TCS shall be capable of being interoperable with the installed payloads across the 5 levels of UAV interaction. SSS322</td></tr><tr><td colspan="3">The TCS shall be capable of being interoperable with multiple platforms/payloads simultaneously.</td></tr><tr><td colspan="3">ORD026</td></tr><tr><td colspan="3"></td></tr><tr><td colspan="3"></td></tr><tr><td colspan="3">ORD027 The TCS shall be capable of meeting the operational and physical security requirements of the SSS362 systems with which it is interoperable.</td></tr><tr><td rowspan="3"></td><td colspan="3">The TCS shall be accredited by the Designated Approving Authority prior to processing classified or sensitive unclassified data. SSS361</td></tr><tr><td colspan="3">The TCS is an automated information system (AIS). As such, as per DoD Regulation 5000.2-R, dated March 15, 1996, the TCS shall meet security requirements in accordance with DoD Directive 5200.28(D), "Security Requirements for Automated Information Systems" dated March 21, 1988. SSS363</td></tr><tr><td colspan="3">procedure defined in DoD 5200.28(D), a risk index and the minimum security requirements for TCS shall be determined. The inputs to this procedure are the clearance or authorization of the TCS users and the sensitivities of the data that the TCS processes, stores or transfers. SSS364 The TCS data sensitivities shall be determined by the data sensitivities of the systems with which it</td></tr><tr><td rowspan="4"></td><td colspan="3">interfaces including the air vehicles, payloads, and C4I systems. The outputs of the procedure are the TCS mode of operation and a digraph that the TCS must minimally satisfy. The digraph (e.g., B1, C2) names the class of security requirements, specified in DoD 5200.28-STD, “Trusted Computer Security Evaluation Criteria (TCSEC)", that the TCS has to satisfy.</td></tr><tr><td colspan="3">SSS365 Links that provide communications between the TCS and other systems shall be secured in a manner appropriate for the sensitivities of the material passed through such links, in accordance with DoD Directive C-5200.5, "Communication Security (COMSEC)" dated 21 April 1990.</td></tr><tr><td colspan="3">SSS366 The TCS shall be designed to protect its communication and data links against enemy Electronic Warfare (EW) threats, physical anti-radiation weaponry and physical destruction.</td></tr><tr><td colspan="3">SSS367 All hardware, software, documentation, and sensitive information processed by TCS shall be physically protected, minimally at the level determined by the risk index computed in Section 3.8.1,</td></tr><tr><td rowspan="4"></td><td colspan="3">to prevent intentional or unintentional disclosure, destruction, or modification. SSS368 The TCS shall be physically secured to the same degree as the systems with which it interfaces</td></tr><tr><td colspan="3">SSS369 All TCS users, operators, maintainers and other personnel having access to TCS shall be cleared to</td></tr><tr><td colspan="3">the highest sensitivity of the data that the TCS processes, stores or transfers. SSS370 Additional local site procedures shall be developed to prevent the intentional or unintentional</td></tr><tr><td colspan="3">71 disclosure of sensitive information to unauthorized individuals. SSS371 A training program consisting of an initial security training and awareness briefing covering AIS</td></tr><tr><td></td><td colspan="3">security in general but also tailored to the TCS shall be developed.</td></tr></table>

<table><tr><td colspan="3">TCS Block 0 TCS 102 Version 2.0 2/12/99</td></tr><tr><td colspan="3">ORD028 The TCS shall be capable of importing NIMA Digital Terrain Elevation Data (DTED), Digital Feature Analysis Data (DFAD), Arc Digitized Raster Graphic and scanned hard copy maps.</td></tr><tr><td rowspan="3"></td><td rowspan="3"></td><td>The TCS computer system shall contain a CD-ROM drive that is compatible with Defense Mapping Agency (DMÅ), CD-ROM Digital Terrain Elevation Data (DTED), Digital Feature Analysis Data (DFAD), and embedded training media</td></tr><tr><td>SSS341 The TCS shall provide a CD drive for the retrieval of TCS data.</td></tr><tr><td>SSS280 The TCS shall be capable of importing National Imagery Mapping Agency (NIMA) Digital Terrain Elevation Data (DTED), Digital Feature Analysis Data (DFAD), Arc Digitized Raster Graphic and scanned hard copy maps, via compact disk.</td></tr><tr><td>ORD029</td><td>The TCS shall be capable of importing map information via operator procedure and should be capable of incorporating vector format and Compressed ADRG (CADRG) maps.</td><td>SSS281 The TCS shall be capable of importing map information via operator procedure and should be capable of incorporating vector format and Compressed ADRG (CADRG) maps.</td></tr><tr><td rowspan="3">ORD030</td><td rowspan="3">The TCS shall include the basic flight planning tools. As a minimum these tools will include 1. Weight and balance take off data calculations.</td><td>SSS555 The TCS shall be capable of importing map information via operator procedure.</td></tr><tr><td>SSS083 The TCS flight route planner shall include, as a minimum, the following flight planning tools: 5. Weight and balance take off data calculations</td></tr><tr><td>SSS088 The TCS shall present to the operator the estimated time of arrival at each programmed waypoint of the proposed mission plan. SSS089</td></tr><tr><td>ORD031</td><td>The TCS shall include the basic flight planning tools. As a minimum these tools will include: 2. Fuel Calculations</td><td>The TCS shall analyze the flight route plan selected for uplink to determine that the flight constraints of the AV and the limitation of the data link are not violated prior to transmission of the flight route plan to the AV. SSS084 The TCS flight route planner shall include, as a minimum, the following flight planning tools: 6. Fuel Calculations</td></tr><tr><td colspan="3">The TCS shall include the basic flight planning tools. As a minimum these tools will include: 3. Terrain avoidance warning and minimum reception altitude calculations for line of sight flights.</td></tr><tr><td rowspan="3">ORD032</td><td rowspan="3"></td><td>SSS085 The TCS flight route planner shall include, as a minimum, the following flight planning tools: 7. Terrain avoidance warning and minimum reception altitude calculations for line of</td></tr><tr><td>sight flights. SSS554 The TCS flight route planner shall include, as a minimum, the following flight planning tools;</td></tr><tr><td>Minimum data link reception altitude calculations for line of sight flights. SSS086 The TCS flight route planner shall include, as a minimum, the following flight planning tools:</td></tr><tr><td>ORD034</td><td>4. Payload search area information such as: visual acuity range due to atmospheric conditions; diurnal transition periods for thermal imagery, and lunar and solar terrain shadowing. The TCS shall be capable of providing point-and-click route and sensor planning.</td><td>9. Payload search area information such as: visual acuity range due to atmospheric conditions; diurnal transition periods for thermal imagery, and lunar and solar terrain shadowing.</td></tr><tr><td rowspan="3"></td><td rowspan="3">SSS092 The TCS shall provide the capability to compute the range and bearing between two geographic</td><td>SSS081 The TCS shall provide the capability to display mission waypoints and flight path graphically.</td></tr><tr><td>SSS059 The TCS mission planning function shall provide a graphical user interface that gives the operator the ability to define waypoints on a map based display using pointing device commands.</td></tr><tr><td>The TCS shall provide the operator with an interactive graphics and map based flight route planning capability. SSS560</td></tr><tr><td rowspan="2">ORD035</td><td rowspan="2">The TCS shall program air vehicles with mission planning data prior to launch.</td><td>positions located on the payload imagery display. SSS561 The TCS shall provide the capability to compute the range and bearing between two geographic</td></tr><tr><td>positions on the map display. SSS070 The TCS shall provide the system functionality necessary to perform flight route plan upload to the AV via the selected system data link or direct ground connection.</td></tr><tr><td colspan="3">ORD036 The TCS shall have tools for importing or creating overlays for fire support coordination measures, airspace control measures, and threat.</td></tr><tr><td rowspan="3"></td><td rowspan="3"></td><td>SSS060 The TCS shall have the ability to import or create map display overlays for fire support coordination measures, airspace control measures, and threat identification measures. SSS087</td></tr><tr><td>The TCS flight route planner shall include, as a minimum, the following flight planning tools: 10. Ability to designate flight corridors and restricted air space. SSS547</td></tr><tr><td>As an objective, the TCS shall have the capability to import as well as create and modify map display overlays for fire support coordination measures. SSS548</td></tr><tr><td>ORD037</td><td>The TCS shall provide the following survivability mission planning features: a. Provide override of payload and AV automated/preprogrammed inputs. SSS174</td><td>The TCS shall have the capability to import as well as create and modify map display overlays for airspace control measures. SSS176 The operator shall be able to manually override the automatic frequency selection if desired</td></tr><tr><td></td><td></td><td>The operator shall be able to manually override the automatic mode selection if desired.</td></tr><tr><td rowspan="3">ORD038</td><td rowspan="3">The TCS shall provide the following survivability mission planning features: b. Provide a method of displaying aircraft signature versus threat, before and during flight.</td><td>SSS163 The operator shall be able to manually override any automatic data terminal control mode selection if desired.</td></tr><tr><td>SSS066 When available, the UAV signature lookup table shall support the capability of displaying aircraft signature versus threat, before and during flight.</td></tr><tr><td>SSS065 Upon completion of radar cross section analysis and characterization by the Government for each UAV type, TCS shall implement a UAV signature versus threat lookup table (database) that identities the lethality of the threat to the UAV.</td></tr></table>

<table><tr><td colspan="2">TCS Block 0 TCS 102 Version 2.0 2/12/99</td></tr><tr><td rowspan="3">ORD039 The TCS shall provide the following survivability mission planning features: c. The system should be capable of displaying overlays or icons of known threat systems and displaying the threat engagement envelopes and associated radar terrain masking for those threats for route planning.</td><td>SSS062 The TCS shall provide the capability of displaying the threat engagement envelopes and associated radar terrain masking for those threats.</td></tr><tr><td>SSS064 An authorized Operator, via the Adjust Programmable Parameters capability, shall be able to modify the maximum number of threats displayed, when de-clutter is selected.</td></tr><tr><td>SSS061 The TCS shall provide the capability of displaying overlays with up to 100 simultaneous icons of known threat systems.</td></tr><tr><td rowspan="5">ORD040 The TCS shall be capable of storing mission plans and exporting them to other TCSs and exporting them to force level mission planning systems.</td><td>SSS549 The TCS shall provide the capability of displaying overlays each containing 100 simultaneous icons of known fire support coordination zones.</td></tr><tr><td>SSS550 The TCS shall provide the capability of displaying overlays each containing 100 simultaneous icons of known airspace control zones</td></tr><tr><td>SSS056 The TCS shall have the functionality to transmit UAV mission plans to other TCSs.</td></tr><tr><td>SSS055 The TCS shall have the functionality to transmit UAV mission plans to service-specific mission planning systems.</td></tr><tr><td>SSS051 The TCS Mission plan shall include all necessary information required to be interoperable with the force level mission planning systems including the Tactical Automated Mission Planning System (TAMPS), Aviation Mission Planning System (AMPS), and Air Force Mission Support System (AFMSS). SSS054 The TCS shall have the functionality to receive UAV mission plans from other TCSs</td></tr></table>

<table><tr><td colspan="3">TCS Block 0 TCS 102 Version 2.0 2/12/99</td></tr><tr><td colspan="3">ORD041 The TCS shall be capable of downloading mission plans from Service-specific mission planning SSS058 systems (e.g., Tactical Aircraft Mission Planning System and Air Force Mission Support System). for later retrieval.</td></tr><tr><td rowspan="3"></td><td rowspan="3"></td><td>The TCS shall be capable of storing a minimum of 500 mission plans under unique names to allow</td></tr><tr><td>SSS053 The TCS shall have the functionality to receive and process UAV mission plans from service- specific mission planning systems.</td></tr><tr><td>SSS106 **DELETED** SSS070</td></tr><tr><td></td><td>The TCS shall be capable of changing the mission plan while the air vehicle is airborne.</td><td>The TCS shall provide the system functionality necessary to perform flight route plan upload to the AV via the selected system data link or direct ground connection.</td></tr></table>

<table><tr><td colspan="2">TCS Block 0 TCS 102 Version 2.0 2/12/99</td></tr><tr><td>ORD043 The TCS shall be ergonomically designed and provide sufficient cues to allow the pilot to safely take off, land, and navigate under Instrument Flight Rules.</td><td>SSS063 A de-clutter capacity shall be provided that only displays the selected number of the most significant threats.</td></tr><tr><td rowspan="6"></td><td>SSS356 Upon detection of loss of link, the TCS shall attempt to reestablish communications with the air vehicle.</td></tr><tr><td>SSS355 The TCS shall monitor the uplink and downlink to each UAV under its control.</td></tr><tr><td>SSS353 The TCS shall be designed such that no single hardware failure or software error results in an unsafe command to be transmitted to and accepted by the air vehicle</td></tr><tr><td>SSS556 The TCS shall be designed such that no single software error results in an unsafe command to be transmitted to the air vehicle.</td></tr><tr><td>SSS352 The TCS shall provide the required information to allow the operator to maintain safe separation from other aircraft and a safe altitude in civilian airspace per Federal Aviation Administration (FAA) rules.</td></tr><tr><td>SSS351</td></tr><tr><td></td><td>During mission execution, the TCS shall provide the operator a caution/warning when the UAV system has identified a malfunction.</td></tr><tr><td rowspan="3"></td><td>SSS350 For mission planning, the TCS shall provide terrain avoidance warning and minimum reception altitude calculations for line of sight flights.</td></tr><tr><td>SSS349 Appropriate caution/warning shall be provided to the operator if the air vehicle deviates into unsafe flight regime.</td></tr><tr><td>SSS348 The TCS shall provide adequate capability to allow the operator to operate each UAV within its certified operational flight envelope.</td></tr><tr><td></td><td>SSS347 The TCS shall provide sufficient cues to allow the operator to safely take-off, land and navigate under Instrument Flight Rules.</td></tr><tr><td rowspan="5">ORD044 The TCS shall support an automatic launch and recovery system.</td><td>SSS135 As an objective, the TCS shall support an automatic launch and recovery system.</td></tr><tr><td>SSS136 As an objective, the TCS shall be interoperable with the Integrity Beacon Landing System (IBLS)</td></tr><tr><td>used by Öutrider. SSS138 As an objective, the TCS shall present sufficient cues to the operator to implement and monitor</td></tr><tr><td>automatic launch and recovery, and to initiate abort procedures if required. SSS289</td></tr><tr><td>The TCS shall provide external interfaces to required launch and recovery systems. SSS137 As an objective, the TCS shall be interoperable with the Common Automated Recovery System</td></tr><tr><td>ORD045 The TCS shall display the location and system status of the UAV.</td><td>SSS143 The TCS shall display the AV status, to include but not be limited to the AV location and system status. SSS144 While the data link is not operational, the TCS shall present the last known AV status values and the</td></tr><tr><td></td><td>time at which the last values were reported. SSS145 The TCS shall be capable of displaying fuel parameters to the operator to include as a minimum fuel status, flow rate, and bingo fuel.</td></tr><tr><td></td><td>SSS146 The TCS shall compute the estimated position of the AV during Loss of Link (LOL) based upon the last known AV position projected along the flight planned route.</td></tr><tr><td>ORD046 The TCS shall display the search footprint of the payload on the moving map.</td><td>SSS536 TCS shall display a LOL timer to the operator initiating a LOL onset.</td></tr><tr><td>ORD047 The TCS shall provide dynamic mission and sensor retasking during operational mission</td><td>SSS157 The TCS shall display the search footprint of the payload on the moving map.</td></tr><tr><td>execution.</td><td>SSS067 The TCS shall permit dynamic mission and sensor retasking during all phases of operational mission execution.</td></tr><tr><td colspan="2">ORD048 The TCS shall receive, process, format, store, retrieve flight and payload data, and perform limited SSS336 exploitation of payload data.</td></tr><tr><td rowspan="7"></td><td>An RS-170A video interface shall be provided for the system to output and input analog imagery and overlays to and from a Video Cassette Recorder (VCR) for recording and playback. SSS334</td></tr><tr><td>The TCS shall allow the Operator(s) to fully control the VCR via the TCS Display input device(s) SSS198</td></tr><tr><td>RS170A Video and digital imagery shall be routed to TCS functions and displayed upon operator request. SSS196</td></tr><tr><td>The TCS operator shall be able to select the content of the overlay information. SSS537</td></tr><tr><td>The TCS shall provide the capability to simultaneously view imagery as well as data from more than one payload, when applicable. SSS195 The TCS shall display live or recorded imagery data, with or without annotation or overlay, upon</td></tr><tr><td>operator request. Annotation includes operator generated comments or graphics which are superimposed on the imagery. Overlays consist of information obtained from external sources that is selected by the operator for presentation with the imagery SSS184 The TCS shall be able to store up to 24 hours of payload data. External storage can be utilized for</td></tr><tr><td>this purpose. SSS182</td></tr><tr><td rowspan="4">ORD049 The TCS shall have the capability to receive data from and control payloads on a UAV that is</td><td>The TCS shall have the functionality to process payload product data from Electro Optical (EO), Infrared (IR), and Synthetic Aperture Radar (SAR) payloads.</td></tr><tr><td>SSS527 The TCS shall provide the system functionality necessary to record data obtained via the data link</td></tr><tr><td>SSS528 The TCS shall be capable of automatically recording system state data, interface communications and other information necessary to support event reconstruction.</td></tr><tr><td>SSS148 The TCS shall have the capability to receive data from and control payloads on an AV that is being controlled from another TĆS.</td></tr></table>

<table><tr><td colspan="3">TCS Block 0 TCS 102 Version 2.0 2/12/99</td></tr><tr><td rowspan="3">ORD050</td><td>The TCS shall provide the capability to pass control of an AV from one TCS to another</td><td>SSS114</td></tr><tr><td></td><td>The TCS shall provide the capability to pass control of an AV to another TCS</td></tr><tr><td>SSS115</td><td>The TCS shall provide the capability to take control of an AV from another TCS.</td></tr><tr><td colspan="3">ORD051 | The TCS shall provide the operator a caution/warning when the UAV system has identified a malfunction.</td></tr><tr><td rowspan="7"></td><td colspan="2">All TCS HCI shall prompt the operator for a valid input if an erroneous entry is made. SSS455</td></tr><tr><td colspan="2">The volume of these auditory tones shall be adjustable by the operator via keyboard and trackball input. SSS453</td></tr><tr><td colspan="2">that important mission data is not obscured. SSS445 The TCS shall provide the operator a caution/warning when the UAV system has identified a</td></tr><tr><td colspan="2">malfunction. SSS448 When performing a given task during mission execution, the operator shall be given appropriate</td></tr><tr><td colspan="2">warning messages from other concurrently-executing subsystem tasks SSS449 TCS Warning messages shall be color coded and flashed based on mission criticality. The color codes and flash frequencies will follow MIL-STD 1472 guidelines</td></tr><tr><td colspan="2">SSS450 The TCS operator shall be required to enter an acknowledgment prior to disabling the display of critical warning flags for any AV, Payload, ADT, GDT, or TCS faults.</td></tr><tr><td colspan="2">SSS452 Visual alerts to the TCS operator shall be in the form of a displayed message box that has a display priority greater than other existing windows to ensure that it is viewable immediately by the</td></tr><tr><td rowspan="4"></td><td colspan="2">operator. SSS454</td></tr><tr><td colspan="2">In addition to displayed alert messages to the TCS operator, auditory alerts/tones shall also be provided. SSS456</td></tr><tr><td colspan="2">All TCS warning messages and HCI actions shall be archived for later review. SSS457</td></tr><tr><td colspan="2">All TCS operator inputs shall be error checked against reasonable minimum and maximum values such that any erroneous operator entry will not cause current processing to terminate.</td></tr></table>

<table><tr><td colspan="3">TCS Block 0 TCS 102 2/12/99</td></tr><tr><td>Version 2.0 ORD052</td><td>The TCS shall enable antenna switching when the UAV is masked by obstructions</td><td>SSS116 For shipboard operations, the TCS shall provide the capability to switch to a second LOS antenna, if a second antenna is available, when the currently active antenna is masked by shipboard obstructions. SSS117 The TCS shall provide the capability to switch to a SATellite COMmunication (SATCOM) antenna, if the selected AV has SATCOM capability, when the AV proceeds beyond LOS range or</td></tr><tr><td>ORD053</td><td>The TCS shall provide limited exploitation capabilities, to include voice and textual reporting for spot/mission objectives.</td><td>when LOS is obstructed. SSS200 The TCS shall have the functionality to conduct limited exploitation on the payload product data. Limited exploitation, as a minimum, will include image enhancement, annotation, and graphic</td></tr><tr><td>ORD054</td><td>The TCS capabilities shall include video/SAR frame grabbing, image annotation, image archiving, video/SAR recording playback, and data dissemination. of these frozen images for further review or processing.</td><td>overlay. SSS330 The TCS shall provide an internal interface for the SAR Processor in order to disseminate SAR information (to include imagery and telemetry) to other components of the TCS. SSS202 The TCS shall provide the capability to capture frozen-frames of imagery and store a limited number</td></tr><tr><td colspan="3">Version 2.0 ORD055 The TCS shall be in compliance with Common Imagery Ground Surface Station (CIGSS), United SSS408</td></tr><tr><td rowspan="6"></td><td rowspan="6">States Imagery Standards (USIS), and GCCS when processing payload imagery data.</td><td>The TACCOM segment shall provide API's for the transmission of imagery in National Imagery Transmission Formats 1.1a and 2.0 as per MILSTD-2500 and in accordance with the Common</td></tr><tr><td>Imagery Ground/Surface Station (CGIS) Guidelines. SSS186 The NITF 2.0 imagery files generated by the TCS shall contain the necessary telemetry and support</td></tr><tr><td>data to permit subsequent imagery exploitation by C4I systems. SSS185 The TCS shall be in compliance with Common Imagery Ground Surface Station (CIGSS), United</td></tr><tr><td>States Imagery Standards (USIS), National Imagery Transmission Format (NITF) Version 2.0 and Global Command Control Systems (GCCS) when processing payload imagery data. The TCS shall have the capability to display Near-Real Time (NRT) imagery with annotation to SSS207</td></tr><tr><td>include date/time group, target location when in the center field of view, north seeking arrow, AV The TCS shall have the functionality to determine the location of items of interest within the payload field of view, and express these locations in coordinates acceptable for military applications.</td></tr><tr><td>SSS206 The TCS shall support a target location function where the operator can request the current ground location of the payload field-of-view center.</td></tr><tr><td rowspan="2">ORD057</td><td rowspan="2">The TCS shall have a built-in word processing and text capability including the ability to overlay</td><td>SSS203 The TCS shall have the capability to display Near-Real Time (NRT) imagery to include, as a minimum, date/time group, target location coordinates when the target is in the center of the field of</td></tr><tr><td>view, north seeking arrow, and AV position and heading SSS187</td></tr><tr><td>textual information on imagery.</td><td></td><td>The TCS shall have a built-in word processing and text capability including the ability to annotate textual information on imagery.</td></tr><tr><td colspan="1" rowspan="1">ORD059</td><td colspan="1" rowspan="1">The TCS shall have a means of inputting data from external data storage systems.</td><td colspan="1" rowspan="1">SSS340The TCS shall have the functionality to transfer digital data or digital imagery to and from externaldata storage devices.SSS339The TCS shall be able to access data storage devices.SSS317The TCS shall provide an interface between the TCS and external data storage systems.SSS318The TCS shall have the functionality to transfer digital data or digital imagery to and from externaldata storage systems</td></tr></table>

TCS Block 0 Version 2.0
<table><tr><td colspan="1" rowspan="1">ORD060</td><td colspan="1" rowspan="1">The TCS shall have the capability to distribute NRT video to selected users (includingcommercially available television monitors and VCRs) via external ports.</td><td colspan="1" rowspan="1">SSS226The TCS shall have the functionality to provide the following control capability:11. Send and receive analog imagery in RS-170A format with or without overlay.SSS219The TCS shall export and disseminate RS-170A video with or without overlay.SSS228The TCS shall have the functionality to provide the following control capability:3.Establish and terminate analog communication to peripheral devices.</td></tr><tr><td colspan="1" rowspan="1">ORD061</td><td colspan="1" rowspan="1">The TCS shall have image enhancement capability</td><td colspan="1" rowspan="1">SSS201The TCS shall have image enhancement capability to include contrast, brightness, edgeenhancement, and sharpness.</td></tr><tr><td colspan="1" rowspan="1">ORD062</td><td colspan="1" rowspan="1">The TCS shall have the capability to select/deselect cross hairs (or other similar ICON) to identifycenter of target.</td><td colspan="1" rowspan="1">SSS197The TCS shall have the capability to select and deselect cross hairs (or other similar ICON) toidentify center of target.</td></tr><tr><td colspan="1" rowspan="1">ORD063</td><td colspan="1" rowspan="1">The TCS shall have the capability to display target symbols in variable sizes</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">ORD064</td><td colspan="1" rowspan="1">The TCS shall have the capability to interoperate with a server to receive, extract, and pushintelligence data.</td><td colspan="1" rowspan="1">SSS212The TCS shall have the capability to interoperate with a data server to receive, extract, and pushintelligence data.SSS374The hardware of the TCS shall be capable of being scaled as well as being modular to meet thevarying needs of the Services.</td></tr><tr><td colspan="3">TCS Block 0 TCS 102 Version 2.0 2/12/99</td></tr><tr><td rowspan="3">ORD065</td><td rowspan="3">The TCS must support a simultaneous uplink and downlink capability TCS shall receive AV telemetry and payload video information via downlink from the AV.</td><td>SSS382 The TCS shall have sufficient throughput to support the processing requirements the selected data link.</td></tr><tr><td>SSS325 The TCS shall support a concurrent uplink and downlink capability SSS324</td></tr><tr><td>The uplink and downlink information passed between the TCS and the AV shall be in accordance with the associated AV documentation SSS111</td></tr><tr><td>ORD066</td><td>The TCS datalink shall provide interfaces with the respective UAV program-provided data links for command and control and UAV data.</td><td>SSS110 TCS shall uplink command and control information to the AV via the uplink to the AV. SSS312 The TCS shall provide interfaces with the respective UAV program-provided data links for</td></tr><tr><td>ORD067</td><td>The TCS datalinks shall comply with CDL standards to ensure interoperability.</td><td>command and control and UAV data. SSS379 The TCS hardware shall support the data rate characteristics of the AV, data link and payload to</td></tr><tr><td>ORD068</td><td>The TCS datalink shall support a simultaneous LOS and beyond LOS capability.</td><td>ensure interoperability. SSS313 The TCS shall have provisions for simultaneously supporting both of the following external</td></tr><tr><td></td><td></td><td>interfaces: LOS data link, SATCOM data link.</td></tr></table>

<table><tr><td>SSS406 The DII/COE UCP/CMP shall provide a consistent and common set of interfaces for United States Military Transmission Format (USMTF), Army Tactical Command Control System (ATCSS), and Field Artillery Tactical Data Systems (FATDS) message sets. TACCOM shall also provide National Imagery Transmission Format (NITF) and system specific interfaces.</td></tr><tr><td>SSS222 The TCS shall have the functionality to provide the following control capability: 1. Send and receive tactical communication messages</td></tr><tr><td>SSS223 The TCS shall have the functionality to provide the following control capability: 2. Send and receive annotated and un-annotated digital imagery</td></tr><tr><td>SSS224 The TCS shall have the functionality to provide the following control capability: Establish and terminate digital communication to the C4I systems specified in Section</td></tr><tr><td>3. 3.2.5. SSS225 The TCS shall have the functionality to provide the following control capability:</td></tr><tr><td>4. Establish and terminate digital communication to peripheral devices. SSS227</td></tr><tr><td>The TCS shall have the functionality to provide the following control capability: 2 Establish and terminate analog communication to C4I systems specified in Section 3.2.5.</td></tr><tr><td>SSS239 The TCS shall have the functionality to monitor the status of all C4I interfaces, and display appropriate control information.</td></tr><tr><td>SSS240 The TCS shall have the functionality to provide the following data monitoring capability; 1. Determine which C4I systems are available and online</td></tr><tr><td>SSS241 The TCS shall have the functionality to provide the following data monitoring capability: 2. Monitor the status of all incoming and outgoing tactical communication messages</td></tr><tr><td>SSS242 The TCS shall have the functionality to provide the following data monitoring capability:</td></tr><tr><td>3. Review all tactical communication messages received or transmitted SSS243 The TCS shall have the functionality to provide the following data monitoring capability:</td></tr><tr><td>4. View either incoming or outgoing, annotated or un-annotated analog imagery SSS244</td></tr></table>

<table><tr><td colspan="1" rowspan="1">ORD070</td><td colspan="1" rowspan="1">The TCS shall have the capability to connect to a local area network.</td><td colspan="2" rowspan="1">SSS288The TCS shall provide the system functionality to allow interfacing with external systems via a localarea network.</td></tr><tr><td colspan="1" rowspan="1">ORD071</td><td colspan="1" rowspan="1">The TCS shall have the capability to use cable to deliver live video imagery in multiple locations.</td><td colspan="2" rowspan="1">SSS213The TCS shall have the capability to use cable to deliver live video imagery in multiple locations.</td></tr><tr><td colspan="1" rowspan="1">ORD072</td><td colspan="1" rowspan="1">The TCS shall have the ability to use Service specific ground or airborne UHF, VHF, andUHF/VHF, and HF radios for digital message transmission while using the same radios for recordtraffic.</td><td colspan="2" rowspan="1">SSS214The TCS shall have the ability to use Service specific ground or airborne Ultra High Frequency(UHF), Very High Frequency (VHF), and UHF/VHF, and High Frequency (HF) radios for digitalmessage transmission while using the same radios for record traffic.</td></tr><tr><td colspan="1" rowspan="1">ORD073</td><td colspan="1" rowspan="1">The TCS shall meet the mission capability criteria established by the MAE UAV and TUAVORDs.</td><td colspan="2" rowspan="1">SSS413The TCS equipment shall achieve an availability (Ao), as defined below, equal to or greater thanthat which is specified in the Predator and Outrider ORDsSSS411The TCS maintainability will be considered in every phase of the design and development processand shall achieve a system maintainability (Mean Time To Repair MTTR) equal to or greater thanthat which is specified in the Predator and Outrider ORDs.SSS410The TCS reliability will be considered in every phase of the design and development process andshall achieve a system reliability (Mean Time Between Failures MTBF) equal to or greater than thatwhich is specified in the Predator and Outrider ORDs.SSS008The TCS shall meet the applicable capability and characteristic criteria established by theOperational Requirements Document (ORD) CAF 003-90-I-A for the RQ-1A Predator MediumAltitude Endurance Unmanned Aerial Vehicle/System (MAE UAV) and the Close Range – TacticalUnmanned Aerial Vehicle (CR-TUAV)</td></tr><tr><td colspan="1" rowspan="1">ORD074</td><td colspan="1" rowspan="1">For each TUAV system, the TCS shall provide full independent computer redundancy</td><td colspan="2" rowspan="1">SSS380For each TUAV system, the TCS shall provide full independent computer redundancy</td></tr><tr><td colspan="1" rowspan="1">ORD075</td><td colspan="1" rowspan="1">The TCS shall be maintained in accordance with the UAV ORD for that Service and the level ofrepair analysis for the hardware chosen</td><td colspan="2" rowspan="1">SSS509The TCS shall be maintained in accordance with the UAV ORD for that Service and the level ofrepair analysis for the hardware chosen.</td></tr><tr><td colspan="3">TCS Block 0 TCS 102 2/12/99</td></tr><tr><td colspan="3" rowspan="3">Version 2.0 ORD076 The TCS shall meet the deployment criteria for the organic unit to which it is assigned.</td></tr><tr><td>SSS516 The TCS shall meet the deployment criteria for the organic unit to which it is assigned.</td></tr><tr><td>SSS523 The TCS shall be sea transportable.</td></tr><tr><td rowspan="3"></td><td rowspan="3"></td><td>SSS522 The TCS shall be air transportable by helicopter (CH-47/CH-53D) and C-130 drive-on/drive-off capable.</td></tr><tr><td>SSS525 The TCS shall be configurable for sea, ground, or air transport in 2 hours or less.</td></tr><tr><td>SSS526 The TCS system shall be capable of being de-configured from sea/ground/air transport and ground- mobile in 2 hours or less.</td></tr><tr><td>ORD077</td><td>The TCS shall use standard military worldwide 110/220 volt 50/60 hertz generators and commercial power sources.</td><td>SSS385 The TCS shall use standard military worldwide 110/220 volt 50/60 hertz generators and commercial power sources</td></tr><tr><td rowspan="3">ORD078</td><td rowspan="3">The TCS shall use standard electrical power sources available within the DOD family of ground mobile, airborne, and shipboard electrical power sources.</td><td>SSS386 The TCS shall use standard electrical power sources available within the DOD family of ground</td></tr><tr><td>mobile, airborne, and shipboard electrical power sources. SSS319 The TCS shall have an interface between the TCS and DoD standard power supply equipment.</td></tr><tr><td>SSS320 The TCS shall have the functionality to connect to the power supply equipment provided in the TCS</td></tr><tr><td>ORD079</td><td>The TCS shall be capable of restoring power in sufficient time to avoid loss of critical mission data or loss of air vehicle control during power outages. The TCS shall be capable of restoring power in sufficient time to avoid loss of critical mission data</td><td>operating environment. SSS354 The TCS shall be capable of restoring power in sufficient time to avoid loss of air vehicle control during power outages. SSS387</td></tr><tr><td colspan="1" rowspan="1">ORD080</td><td colspan="1" rowspan="1">The TCS shall have an uninterrupted power supply for critical phases (landing and takeoff as aminimum) of mission execution.</td><td colspan="1" rowspan="1">SSS344The TCS shall have an interface to an uninterruptible power supply.SSS388The TCS shall have an uninterrupted power supply for critical phases (landing and takeoff as aminimum) of mission execution.</td></tr><tr><td colspan="1" rowspan="1">ORD081</td><td colspan="1" rowspan="1">The TCS shall have an objective capability to be integrated and operated from tactical andcommand and control aircraft and submarines.</td><td colspan="1" rowspan="1">SSS534The TCS shall have the capability to be integrated and operated from ships.SSS533The TCS shall have the capability to be integrated and operated from land based platforms.SSS531The TCS shall have the capability to be integrated and operated from tactical and command andcontrol aircraft.SSS532The TCS shall have the capability to be integrated and operated from submarines.</td></tr><tr><td colspan="1" rowspan="1">ORD082</td><td colspan="1" rowspan="1">The TCS shall operate in world wide climatic conditions, i.e. same climatic conditions in which theTCS shelter/platform is designed to operate.</td><td colspan="1" rowspan="1">SSS372The TCS shall be capable of operation within environments specified for the land-based shelter andshipboard environments.SSS435The TCS shall be compatible with the external electromagnetic environment.</td></tr><tr><td colspan="1" rowspan="1">ORD083</td><td colspan="1" rowspan="1">A TCS support and fielding package shall be developed and available for operational testing.</td><td colspan="1" rowspan="1">SSS510A TCS support and fielding package shall be developed and available for operational testing</td></tr><tr><td colspan="1" rowspan="1">ORD084</td><td colspan="1" rowspan="1">The TCS shall be maintained in accordance with Services' approved UAV maintenance conceptsand procedures.</td><td colspan="1" rowspan="1">SSS511The TCS shall be maintained in accordance with Services' approved UAV maintenance concepts andprocedures.</td></tr><tr><td colspan="1" rowspan="1">ORD085</td><td colspan="1" rowspan="1">Support for the TCS shall be in accordance with the Integrated Logistical Support Plan (ILSP) andthe maintenance concepts and policies of the individual Services.</td><td colspan="1" rowspan="1">SSS504Support for the TCS shall be in accordance with the Integrated Logistical Support Plan (ILSP) andthe maintenance concepts and policies of the individual Services.</td></tr><tr><td colspan="1" rowspan="1">ORD086</td><td colspan="1" rowspan="1">Standard tools, TMDE, repair parts, and lubricants shall be used to maintain the TCS</td><td colspan="1" rowspan="1">SSS507Standard tools, TMDE, repair parts, and lubricants shall be used to maintain the TCS. Exceptionsshall be considered on a case by case basis.</td></tr></table>

TCS Block 0   
Version 2.0

<table><tr><td>ORD087</td><td colspan="2">To the maximum extent possible, general purpose test equipment (GPTE) and common tools SSS512</td></tr><tr><td></td><td></td><td>authorized levels of maintenance. SSS513 Tools and test equipment required to maintain the TCS but not resident in each service inventory shall be identified as special tools and special purpose test equipment (SPTE), respectively, and kept</td></tr><tr><td>ORD088</td><td>Tools and test equipment required to maintain the TCS but not resident in each service inventory shall be identified as special tools and special purpose test equipment (SPTE), respectively, and</td><td></td></tr><tr><td>ORD089</td><td>kept to a minimum. The TCS hardware and software shall include FD/L during initial computer system boot-up.</td><td>SSS025 Initialization of the TCS shall include execution of Startup FD/L. SSS024</td></tr><tr><td></td><td></td><td>When executing in the Normal Startup Mode, the TCS shall provide the system functionality necessary to execute the Startup Fault Detection Logic (FD/L) and initialize the system to place it in the Operations State within 60 seconds. SSS249</td></tr><tr><td></td><td></td><td>Fault Detection/Location (FD/L) to the Line Replaceable Unit (LRU) level shall be provided to indicate the readiness status of TCS, if inherent to the COTS hardware and software utilized..</td></tr><tr><td></td><td></td><td>SSS250 As a minimum, TCS shall provide Startup FD/L for the operator workstation.</td></tr><tr><td></td><td></td><td>SSS036 The TCS hardware and software shall execute periodic Fault Detection Logic (FD/L) while in the Normal Operations Mode and Training Mode, to include a periodic determination of level of</td></tr><tr><td>ORD090</td><td>The TCS manpower requirements shall not exceed the Services&#x27; guidelines for their respective</td><td>interaction.</td></tr><tr><td>ORD091</td><td>UAV Program. TCS training shall be balanced between institutional, New Equipment Training (NET), and unit</td><td></td></tr><tr><td>ORD092</td><td>training. TCS instructor and key personnel training shall be required.</td><td></td></tr><tr><td>ORD093</td><td>TCS units shall receive NET as new system equipment is fielded.</td><td></td></tr><tr><td>ORD094</td><td>TCS training devices shall be required for the institutional training base.</td><td></td></tr></table>

<table><tr><td colspan="4">TCS Block 0 TCS 102 2/12/99</td></tr><tr><td colspan="4">Version 2.0</td></tr><tr><td rowspan="3">ORD095 collective modes.</td><td>TCS unit training shall be conducted in both garrison and field environments -- individual and </td><td colspan="2">SSS491 TCS training and training support shall include the processes, procedures, techniques, training devices and equipment to train civilian, active duty and reserve military personnel to operate and</td></tr><tr><td></td><td colspan="2">support the TCS system. This will include: individual and crew training; new equipment training; initial, formal, and on-the-job training. TCS training will strike a balance between institutional, new</td></tr><tr><td>equipment and unit training.</td><td colspan="2"></td></tr><tr><td colspan="3">TCS Block 0 TCS 102 Version 2.0 2/12/99</td></tr><tr><td colspan="3">ORD096 The TCS system shall provide, for the operator and maintainer, the capability for incorporation of SSS492 embedded / add-on interactive training with self-paced instruction, duplicating UAV flight</td></tr><tr><td rowspan="6"></td><td rowspan="6">performance characteristics, capabilities, and limitations.</td><td>The TCS system shall provide, for the operator and maintainer, an embedded or add-on interactive training courseware with self-paced instruction, duplicating UAV flight performance characteristics, capabilities, and limitations</td></tr><tr><td>SSS402 Training software shall be alterable without affecting the configuration of the operational software.</td></tr><tr><td>SSS494 The interactive courseware training capability for TCS shall be developed during Phase I and introduced to the user during scheduled demonstrations and tests.</td></tr><tr><td>SSS495 The training capability for performance of TCS functions shall include primary mission (flight route/payload) planning, mission control and monitoring, imagery processing, tactical communications, AV control communications and TCS system on line diagnostics. This capability will be qualified and improved during Phase I based upon use and feedback from qualified operators and users demonstrating TCS system equipment throughout Phase I. Instructional support materials</td></tr><tr><td>and training courseware for classroom discussion and lecture will be developed to support institutional, new equipment training and unit training SSS496 The TCS shall provide the functional capability to train personnel in the operation of the TCS</td></tr><tr><td>system, performance of TCS UAV functions, and on-line system troubleshooting. SSS497 TCS system training shall include system architecture, component familiarization, and system startup, initialization, system recovery, on-line diagnostics, and shutdown,</td></tr><tr><td rowspan="4"></td><td>SSS501</td><td>Training shall be adequate to maintain operator and maintainer skills and proficiencies.</td></tr><tr><td>SSS502</td><td>TCS shall record operator and maintainer actions for self assessment and performance enhancement.</td></tr><tr><td>SSS503 Operator and maintainer performance shall be measurable using parameters retrievable from the</td><td></td></tr><tr><td>SSS493 The TUAV TCS system shall be compatible with the U.S. Army Intelligence and Electronic Warfare</td><td>TCS to determine proficiency levels.</td></tr><tr><td>ORD097</td><td>The TUAV TCS system shall be compatible with the U.S. Army Intelligence and Electronic Warfare Tactical Proficiency Trainer (Multiple UAV Simulation Environment) as an objective.</td><td>Tactical Proficiency Trainer as an objective</td><td></td></tr></table>

<table><tr><td colspan="1" rowspan="1">ORD098</td><td colspan="1" rowspan="1">All TCS Operator Manuals and Technical Manuals shall be verified and validated prior to initialoperational test.</td><td colspan="1" rowspan="1">SSS529All TCS Operator Manuals and Technical Manuals shall be verified and validated prior to initialoperational test.</td></tr><tr><td colspan="1" rowspan="1">ORD099</td><td colspan="1" rowspan="1">TCS system safety and health hazards, if any, shall be identified and evaluated.</td><td colspan="1" rowspan="1">SSS359System safety and health hazards, if any, shall be identified and evaluated.SSS357The TCS design shall provide protection against injury to TCS operators and maintenancepersonnel.SSS345The TCS design solution shall consider all safety requirements affecting design and performanceexcept nuclear safetySSS436The TCS design shall ensure that personnel, fuel, and ordinance are not exposed to electromagneticradiation.SSS358The TCS system design shall use MIL-STD-2036, Section 5.1.3.11 as a guide, with regard topersonnel hazards, and MIL-STD-1472D, Section 5.13, as a guide for safety from a humanengineering viewpoint.</td></tr><tr><td colspan="1" rowspan="1">ORD100</td><td colspan="1" rowspan="1">TCS risk levels and a program to manage the probability and severity of hazards shall bedeveloped.</td><td colspan="1" rowspan="1">SSS360Risk levels and a program to manage the probability and severity of hazards shall also be developed.SSS346The TCS safety requirements are intended to eliminate or control potential hazards to equipment andpersonnel involved in the TCS. The TCS shall comply with para 5.3 of MIL-STD 882C, "SystemSafety Program Requirements", dated 19 January 1993 w/Notice 1 dated 19 January 1996.</td></tr><tr><td colspan="1" rowspan="1">ORD101</td><td colspan="1" rowspan="1">The TCS shall conform with the National Institute for Standard Technology (NIST) FederalInformation Processing Standard (FIPS) Publication 151-2 (POSTX.1)</td><td colspan="1" rowspan="1">SSS381The TCS shall conform with the National Institute for Standard Technology (NIST) FederalInformation Processing Standard (FIPS) Publication 151-2 (POSIX.1)</td></tr><tr><td colspan="1" rowspan="1">ORD102</td><td colspan="1" rowspan="1">The TCS shall be capable of providing a 50% spare memory storage capacity over deliveredstorage used.</td><td colspan="1" rowspan="1">SSS391The TCS shall be capable of providing a 50% spare memory storage capacity over delivered storageused.</td></tr><tr><td colspan="1" rowspan="1">ORD103</td><td colspan="1" rowspan="1">A 75% spare memory storage capacity over storage used is desired.</td><td colspan="1" rowspan="1">SSS392The TCS shall be capable of providing a 75% spare memory storage capacity over storage used(objective).</td></tr><tr><td colspan="1" rowspan="1">ORD104</td><td colspan="1" rowspan="1">To meet growth requirements, the TCS should be capable of adding additional storage without amajor hardware reconfiguration.</td><td colspan="1" rowspan="1">SSS383To meet growth requirements, the TCS shall be capable of adding additional storage without majorhardware reconfiguration</td></tr><tr><td colspan="1" rowspan="1">ORD105</td><td colspan="1" rowspan="1">The TCS throughput shall not exceed 50% of throughput capability delivered. Throughput shouldnot exceed 25% of throughput capability delivered (objective).</td><td colspan="1" rowspan="1">SSS390The TCS throughput shall not exceed 25% of throughput capability delivered (objective).SSS389The TCS throughput shall not exceed 50% of throughput capability delivered.SSS415The processing speed of each processor shall be such that at least 50% of the throughput of eachprocessor remains unused during all 10 second periods and at least 20% of the throughput of eachprocessor remains unused during all one second periods regardless of the system function performed.SSS416The I/O channel reserve capability for each processor shall have at least a 50% reserve, addressableand useable, I/O channel capacity.</td></tr><tr><td colspan="1" rowspan="1">ORD106</td><td colspan="1" rowspan="1">The TCS shall comply with the Assistant Secretary of Defense (C3I) Joint Technical Architecture(JTA). This includes, but is not limited to, the language, the computer, database, architecture, andinteroperability</td><td colspan="1" rowspan="1">SSS394The TCS shall comply with the Assistant Secretary of Defense (C3I) Joint Technical Architecture(JTA). This includes, but is not limited to, the language, the computer, database, architecture, andinteroperability.SSS567All TCS HWCI's and CSCI's shall be Year 2000 compliant</td></tr><tr><td colspan="1" rowspan="1">ORD107</td><td colspan="1" rowspan="1">The TCS hardware shall be mounted and/or ruggedized to withstand inter and intra theatermovement.</td><td colspan="1" rowspan="1">SSS373The TCS hardware shall be mounted and/or ruggedized to withstand inter and intra theatermovement.</td></tr><tr><td colspan="1" rowspan="1">ORD108</td><td colspan="1" rowspan="1">TCS containers must be reusable and enable the operators to set-up equipment within theestablished timelines in their ORDs.</td><td colspan="1" rowspan="1">SSS505TCS transport and storage containers shall be reusable and enable the operators to set-up equipmentwithin the established timelines in their ORDs.</td></tr><tr><td colspan="1" rowspan="1">ORD109</td><td colspan="1" rowspan="1">The TCS shall support direct connectivity to standard DOD tactical (VHF, UHF, and UHF/VHF)radios, Mobile Subscriber Equipment, and military/commercial satellite communicationscapabilities.</td><td colspan="1" rowspan="1">SSS285The TCS shall provide the capability to interface with equipment necessary to provide connectivitywith standard DOD tactical (VHF, UHF, and UHF/VHF) radios, Mobile Subscriber Equipment, andmilitary and commercial satellite communications equipment.</td></tr><tr><td>ORD110</td><td>The TCS shall be capable of entering DII-COE compliant (C4I) networks. Network SSS209 interoperability shall include, but not be limited to: 1. Radio data burst connectivity to Automatic Target Hand-off Systems (ATHS) 2. Advanced Field Artillery Tactical Data Systems (AFATDS) SSS291 3. Army Deep Operations Coordination System (ADOCS) 4. Wire connectivity to the All Source Analysis System (ASAS) 5. The Intelligence Analysis System (IAS) 6. The Joint Standoff Target Attack Radar System (JSTARS) Ground Station Module/Common SSS292 Ground Station (GSM/CGS) The TCS shall provide the necessary hardware and software functionality to allow the TCS to</td><td>The TCS shall be capable of entering DII-COE compliant (C4I) networks. The TCS shall provide the necessary hardware and software functionality to allow the TCS to integrate with AŠAS.</td></tr><tr><td colspan="3">7. The Joint Maritime command Information System (JMCIS) 8. Closed Circuit Television (CCTV) 9. Advanced Tomahawk Weapons Control Station (ATWCS) 10. Joint Deployable Intelligence Support System (JDISS) 11. Trojan Special Purpose Integrated Remote Intelligence Terminal (SPIRIT) 12. Joint Service Imagery Processing System (JSIPS) 13. JSIPS Tactical Exploitation Group (JSIPS TEG) 14. JSIPS Tactical Exploitation System (JSIPS TES) 15. Service Mission Planners 16. The Theater Battle Management Core System (TBMCS) 17. The Guardrail Common Sensor/Aerial Common Sensor (GCS/ACS) Integrated Processing Facility 18. Modernized Imagery Exploitation System (MIES) 19. Enhanced Tactical Radar Correlator (ETRAC) 20. Contingency Airborne Reconnaissance System (CARS) 21. Common Operational Modeling, Planning, and Simulation System (COMPSS)</td></tr><tr><td colspan="1" rowspan="1">ORD111</td><td colspan="1" rowspan="1">The TCS shall be transported into the theater as an organic component of the operational UAVsystem being deployed.</td><td colspan="1" rowspan="1">SSS517The TCS shall be transported into the theater as an organic component of the operational UAVsystem being deployed.</td></tr><tr><td colspan="1" rowspan="1">ORD112</td><td colspan="1" rowspan="1">TCS transportation in theater for Army and Marine Corps systems shall be by ground transport,air, or rail.</td><td colspan="1" rowspan="1">SSS518TCS transportation in theater for Army and Marine Corps systems shall be by ground transport, air,or rail.SSS521The TCS shall be ground transportableThe TCS shall be air transportableSSS524The TCS shall be rail transportable.</td></tr><tr><td colspan="1" rowspan="1">ORD113</td><td colspan="1" rowspan="1">For the Air Force, TCS transportation to the theater shall be by air</td><td colspan="1" rowspan="1">SSS519For the Air Force, TCS transportation to the theater shall be by air.The TCS shall be air transportable</td></tr><tr><td colspan="1" rowspan="1">ORD114</td><td colspan="1" rowspan="1">Within the theater, the USAF GCS shall be capable of being moved around an established air field.</td><td colspan="1" rowspan="1">SSS520Within the theater, the USAF GCS shall be capable of being moved around an established air field.The TCS shall be air transportable</td></tr><tr><td colspan="1" rowspan="1">ORD115</td><td colspan="1" rowspan="1">Basing for the system will follow the plan for UAV units and service command echelonrequirements as delineated in paragraph 6 below.</td><td colspan="1" rowspan="1">SSS515Basing for the system shall follow the plan for UAV units and service command echelonrequirements as delineated in the ORD.</td></tr><tr><td colspan="1" rowspan="1">ORD116</td><td colspan="1" rowspan="1">TCS data burst messages shall comply with Variable Message Formats.</td><td colspan="1" rowspan="1">SSS215Where applicable, TCS data burst messages shall comply with Variable Message Formats.</td></tr><tr><td colspan="1" rowspan="1">ORD117</td><td colspan="1" rowspan="1">The TCS shall adhere to DOD regulations and policy governing military standards for logistics,POL, tools, TMDE, and other support items.</td><td colspan="1" rowspan="1">SSS506The TCS shall adhere to DOD regulations and policy governing military standards for logistics,Petroleum, Oil and Lubricants (POL), tools, Test, Measurement, and Diagnostic Equipment(TMDE), tools, and other support items.</td></tr><tr><td colspan="1" rowspan="1">ORD118</td><td colspan="1" rowspan="1">The TCS shall require support from NIMA for digitized map displays with elevation data.</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">ORD119</td><td colspan="1" rowspan="1">The environmental support required by the TCS shall be the same as that required for therespective UAV System.</td><td colspan="1" rowspan="1">SSS514The environmental support required by the TCS shall be at least the same as that required for therespective UAV System.</td></tr></table>

APPENDIX B: MAE Applicable Capability Criteria and Characteristics
<table><tr><td colspan="2">Capabilities and Characteristics</td><td>Thresholds</td><td>Objectives</td><td>TCS RQMT TRACIN G NUMBER</td><td>TCS ORD Compatibl e With Threshold</td><td>TCS RQMT TRACIN G NUMBE R</td><td>TCS O1 Compati with Objecti</td></tr><tr><td colspan="2">1. Flight Vehicle Performance a. Ground Operations (4.1.1.1)</td><td>Operate from airfield with other. aircraft</td><td></td><td>MAE0000 1</td><td>N/A</td><td></td><td></td></tr><tr><td colspan="2">b. Runway Requirements</td><td>8000 ft x 125 ft 50 ft taxiways</td><td>3000 ft</td><td>MAE0000 2</td><td>N/A</td><td>MAE0010 5</td><td>N/A</td></tr><tr><td colspan="2">c. Take-off &amp; Landing in a crosswind with LOS Link @ 14kts</td><td></td><td>with SATCOM @ 20 MAE0000 kts</td><td>3</td><td>N/A</td><td>MAE0010 6</td><td>N/A</td></tr><tr><td colspan="2">d. system)</td><td>Combat Capabilities (baseline Operations from FLOT (100-150 NM) . to Rear of 2nd echelon up to 400 NM from operating base</td><td></td><td>MAE0000 4</td><td>N/A</td><td></td><td></td></tr><tr><td colspan="2"></td><td>Continuous 24 hour intelligence . coverage (with on station relief) of any</td><td></td><td>MAE0000 5</td><td>N/A</td><td></td><td></td></tr><tr><td colspan="2">e. Sustained flight operations altitudes &gt;/= 15000 ft MSL</td><td>target in the operating area</td><td>&gt; 25000 ft MSL</td><td>MAE0000 6</td><td>N/A</td><td>MAE0010 7</td><td>N/A</td></tr><tr><td colspan="2">Capabilities and Characteristics</td><td>Thresholds</td><td>Objectives</td><td>TCS RQMT TRACIN G NUMBER</td><td>TCS ORD Compatibl e With Threshold</td><td>TCS RQMT TRACIN G NUMBE</td><td>TCS 01 Compati with Objecti</td></tr><tr><td colspan="2">f. Cruise Speed</td><td>Sufficient to successfully employ the Sufficient sensors while operating at 15000 ft successfully employ MSL</td><td>the sensors while operating at &gt;25000</td><td>to MAE0000 7</td><td>N/A</td><td>R MAE0010 8</td><td>N/A</td></tr><tr><td colspan="2">1.1 communications</td><td>Ku SATCOM / CDL</td><td>ftMSL VHF/HF/tactical data MAE0000 link</td><td>8</td><td>N/A</td><td>MAE0010 9</td><td>N/A</td></tr><tr><td colspan="2">1.2 Airspace coordination Equipment Through UHF/VHF radio during both .</td><td>LOS and BLOS operations</td><td></td><td>MAE0000 9</td><td>N/A</td><td></td><td></td></tr><tr><td colspan="2">a. In flight communication between GCS and Airspace controlling</td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td colspan="2">agency b. Identification Friend or Foe (IFF)</td><td>Mode I / II / III / IV</td><td>Mode S</td><td>MAE0001 0</td><td>N/A</td><td>MAE0011 0</td><td>N/A</td></tr><tr><td colspan="2"></td><td></td><td>Emergency Locator Transmitter (ELT)</td><td></td><td></td><td>MAE0011 1</td><td>N/A</td></tr><tr><td colspan="2">Capabilities and Characteristics</td><td rowspan="2">Thresholds</td><td rowspan="2">Objectives</td><td rowspan="2">TCS RQMT TRACIN G NUMBER</td><td rowspan="2">TCS ORD Compatibl e With Threshold</td><td rowspan="2">TCS RQMT TRACIN G NUMBE</td><td rowspan="2">TCS OI Compati with Objecti</td></tr><tr><td></td><td></td></tr><tr><td rowspan="2">c. Navigation systems</td><td>Verifiable via LPI methods (i.e.) GPS Navigation</td><td>accuracy Primary</td><td>system MAE0001 to meet 1 Mission</td><td>N/A</td><td>R MAE0011 2</td><td>N/A</td></tr><tr><td>Maximize access for on-equipment .</td><td>Eqpt (PME) sensor requirements</td><td>MAE0001</td><td>N/A</td><td></td><td></td></tr><tr><td>a. Engine designed to b. Engine capable of</td><td>maintenance or inspection</td><td>In-flight restart</td><td>2</td><td></td><td>MAE0011</td><td>N/A</td></tr><tr><td></td><td></td><td>Unassisted</td><td>Ground</td><td></td><td>3 MAE0011</td><td>N/A</td></tr><tr><td>c. Engine capable of</td><td>Anti icing sensor and equipment</td><td>Start</td><td>MAE0001</td><td>N/A</td><td>4</td><td></td></tr><tr><td>1.4 Anti Icing</td><td>Search / Detect and allow recognition</td><td></td><td>3 MAE0001</td><td>N/A</td><td></td><td></td></tr><tr><td>2. Sensor Packages (4.1.2.1)</td><td>of tactical size targets</td><td></td><td>4</td><td></td><td></td><td></td></tr><tr><td></td><td>at 30000 ft</td><td>at 60000 ft</td><td>MAE0001 5</td><td>N/A</td><td>MAE0011 5</td><td>N/A</td></tr><tr><td rowspan="2">Capabilities and Characteristics</td><td rowspan="2">Thresholds</td><td rowspan="2">Objectives</td><td rowspan="2">TCS RQMT TRACIN G NUMBER</td><td rowspan="2">TCS ORD Compatibl e With Threshold</td><td rowspan="2">TCS RQMT TRACIN G NUMBE R</td><td rowspan="2">TCS OI Compati with Objecti</td></tr><tr><td></td></tr><tr><td>a. EO/IR/SAR &amp; Recorder</td><td>Multi-module</td><td>Single Module</td><td>MAE0001 6</td><td>N/A</td><td>MAE0011 6</td><td>N/A</td></tr><tr><td></td><td>Designed for quick insert and removal</td><td></td><td>MAE0001 7</td><td>N/A</td><td></td><td></td></tr><tr><td>b. Sensor protection</td><td>Dust, moisture, icing, rain, sleet, snow, Laser, and hail</td><td>microwave</td><td>NBC, MAE0001 8</td><td>N/A</td><td>MAE0011 7</td><td>N/A</td></tr><tr><td>c. Search</td><td>tailored area surveillance (i.e. strip . search)</td><td></td><td>MAE0001 9</td><td>N/A</td><td></td><td></td></tr><tr><td>d. Detect</td><td></td><td>Target detection in clutter</td><td></td><td></td><td>MAE0011 8</td><td>N/A</td></tr><tr><td>e. CLASSIFIED</td><td>CLASSIFIED</td><td>CLASSIFIED</td><td>MAE0002 0</td><td>?</td><td>MAE0011 9</td><td>?</td></tr><tr><td>f. Classify / identify 3 meter sq. targets Tracked vs. wheeled</td><td></td><td>T-72 VS. &gt;90% of the time</td><td>M-1A1 MAE0002 1</td><td>N/A</td><td>MAE0012 0</td><td>N/A</td></tr><tr><td></td><td></td><td>BDA Capability</td><td></td><td></td><td>MAE0012 1</td><td>N/A</td></tr><tr><td>2.1 Re-task of Sensors (4.1.2.2)</td><td></td><td>GCS to be JTT equipped</td><td></td><td></td><td>MAE0012 2</td><td>N/A</td></tr></table>

<table><tr><td rowspan="2">Capabilities and Characteristics</td><td rowspan="2">Thresholds</td><td rowspan="2">Objectives</td><td rowspan="2">TCS RQMT TRACIN G NUMBER</td><td rowspan="2">TCS ORD</td><td rowspan="2">TCS TCS 01 RQMT Compati TRACIN G Objecti NUMBE R</td></tr><tr><td>Compatibl e With Threshold</td></tr><tr><td>2.2 Airborne Mass Storage Device Included as part of airborne PME</td><td>Manual from the GCS by Sensor Auto re-task using MAE0002 Operator</td><td>ATC/ATR input 2 compatible with MAE0002</td><td>N/A N/A</td><td>MAE0012 3 MAE0012</td><td>N/A N/A</td></tr><tr><td>(4.1.2.3)</td><td>assets</td><td>other USAF Recce</td><td>3</td><td>4</td><td></td></tr><tr><td>3.0 Ground Control System (4.1.3)</td><td>Air transport by C-130 &amp; supportable . at forward bases</td><td></td><td>MAE0002 4</td><td>YES</td><td></td></tr><tr><td>Vehicle Control 3.1 </td><td>Active control of one with one in Control ready loiter status Mission Planning Subsystem Route and route segments and sensor weather and</td><td>multiple MAE0002 vehicles at once 1 other MAE0002</td><td>YES 5 YES</td><td>MAE0012 5</td><td>YES</td></tr><tr><td>(4.1.3.1)</td><td>tasking</td><td>package assets (SEAD) in mission</td><td>6</td><td>MAE0012 6</td><td>?</td></tr><tr><td>a. Generate b. Compatible</td><td></td><td>with AFMSS</td><td></td><td>MAE0012</td><td>YES</td></tr><tr><td>c. Contained within or interface with</td><td></td><td>Intel tasking,</td><td></td><td>7 MAE0012</td><td>YES</td></tr><tr><td></td><td></td><td>collection, processing, and dissemination</td><td></td><td>8</td><td></td></tr><tr><td colspan="6">TCS Block 0 TCS 102</td></tr><tr><td>Version 2.0 Capabilities and Characteristics</td><td>Thresholds</td><td>Objectives</td><td>TCS RQMT TRACIN</td><td>TCS ORD Compatibl e With</td><td>2/12/99 TCS RQMT TRACIN</td><td>TCS OI Compati</td></tr><tr><td></td><td></td><td>Aircraft signature vs.</td><td>G NUMBER</td><td>Threshold</td><td>G NUMBE R MAE0012</td><td>with Objecti</td></tr><tr><td>d. Display</td><td>Perform real time mission control, </td><td>threat</td><td>MAE0002</td><td>YES</td><td>9</td><td>YES</td></tr><tr><td>3.2 Mission Execution (4.1.3.1.1) a. Ergonomically designed</td><td>monitoring, updates, mods</td><td></td><td>7</td><td></td><td></td><td></td></tr><tr><td>operator control: Function Keys, joy sticks, trackball, programmable switch arrays to</td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>b. In-flight change between Of track and sensor assignments preplanned and real time missions</td><td></td><td></td><td>MAE0002 8</td><td>YES</td><td></td><td></td></tr><tr><td>C. Receive, process, disseminate, From single platform format, store, retrieve sensor data and</td><td></td><td>From platforms</td><td>multiple MAE0002 9</td><td>YES</td><td>MAE0013 0</td><td>YES</td></tr><tr><td>perform imagery screening/quality control of sensor data</td><td></td><td></td><td>MAE0003</td><td></td><td></td><td></td></tr><tr><td>d. Operator will be able to command Sensor calibration, updates / scene .</td><td>insertion / mass storage device control</td><td></td><td>0</td><td>YES</td><td></td><td></td></tr><tr><td>3.3 Imagery Processing (4.1.3.1.2)</td><td>CIGSS</td><td>DCGS/USIS</td><td>MAE0003</td><td>YES</td><td>MAE0013</td><td>YES</td></tr><tr><td>a. System will adhere to current Standards for imagery exploitation</td><td></td><td></td><td>1</td><td></td><td>1</td><td></td></tr><tr><td>Capabilities and Characteristics</td><td>Thresholds</td><td>Objectives</td><td>TCS RQMT TRACIN G NUMBER</td><td>TCS ORD Compatibl RQMT e With TRACIN Threshold</td><td>TCS G NUMBE</td><td>TCS 01 Compati with Objecti</td></tr><tr><td rowspan="7">b. (4.1.3.1.2.1)</td><td>The workstation must have Ports for outputting data and imagery . to printer and magnetic media</td><td></td><td>MAE0003 2</td><td>YES</td><td>R</td><td></td></tr><tr><td>a means of inputting data from external magnetic media</td><td></td><td>MAE0003 3</td><td>YES</td><td></td><td></td></tr><tr><td>Image enhancement manipulation</td><td></td><td>MAE0003 4</td><td>YES</td><td></td><td></td></tr><tr><td></td><td>Target symbols in various sizes</td><td></td><td></td><td>MAE0013 2</td><td>YES</td></tr><tr><td>automatic framing to designate the . sub-image display are for detailed exploitation with screening or image selection to designate targets or target</td><td></td><td>MAE0003 5</td><td>YES</td><td></td><td></td></tr><tr><td>frames within a mission as the imagery is received Cross hairs or other ICON identification of center of target on the</td><td></td><td>MAE0003</td><td>YES</td><td></td><td></td></tr><tr><td>display or target outline or ellipse (along with x, y, z data)</td><td></td><td>6</td><td></td><td></td><td></td></tr><tr><td colspan="6">TCS Block 0 TCS 102 Version 2.0</td></tr><tr><td>Capabilities and Characteristics</td><td>Thresholds</td><td>Objectives</td><td>TCS RQMT TRACIN</td><td>TCS ORD Compatibl e With Threshold</td><td>2/12/99 TCS RQMT TRACIN</td><td>TCS OI Compati with</td></tr><tr><td colspan="3">All imagery input must be converted .</td><td colspan="3">G NUMBER</td><td>G Objecti NUMBE R</td></tr><tr><td colspan="3">into NITFS 2.0 collateral</td><td>MAE0003 7 USIS</td><td>YES</td><td></td><td></td></tr><tr><td colspan="3"></td><td>IPL/IPA in the GCS to receive, extract and push intelligence</td><td></td><td>MAE0013 3</td><td>YES</td></tr><tr><td colspan="3">3.4 Mission Launch and recovery Ergonomically designed and provide Automatic Subsystem (4.1.3.2) Take-Off and Land and navigate under</td><td>data launch MAE0003 sufficient cues to allow pilot to safely and recovery system</td><td>YES 8</td><td>MAE0013 4</td><td>YES</td></tr><tr><td colspan="3">IFR conditions 3.5 Communications Subsystems Secure / Non-secure Interfaces Provide Interfaces to existing</td><td>Feed CIGSS/USIS systems</td><td>all MAE0003 YES 9</td><td>MAE0013</td><td>YES</td></tr><tr><td colspan="3">worldwide and local comm. systems (4.1.3.3)</td><td>in theater</td><td></td><td>5</td><td></td></tr><tr><td colspan="3">3.6 Data Links (4.1.3.4) LOS or BLOS Data simultaneously</td><td>Simultaneous Video MAE0004</td><td>YES</td><td>MAE0013</td><td>N/A</td></tr><tr><td colspan="3">a. Uplink and downlink</td><td>Phase History, EO/IR &amp; SAR data</td><td>0</td><td>6</td><td></td></tr><tr><td rowspan="2">Capabilities and Characteristics</td><td rowspan="2">Thresholds</td><td rowspan="2">Objectives</td><td rowspan="2">TCS RQMT TRACIN G NUMBER</td><td rowspan="2">TCS ORD Compatibl e With</td><td rowspan="2">TCS TCS OI RQMT Compati TRACIN G Objecti NUMBE R</td></tr><tr><td>Threshold</td></tr><tr><td>b. LOS Link CDL Compliant</td><td>Simultaneous LOS/BLOS</td><td>MAE0004 1</td><td>YES YES</td><td>MAE0013 7</td><td>YES</td></tr><tr><td>3.7 Ground communications (4.1.3.5) Provide link to significant external . 3.7.1 MAE Comm support capability</td><td>databases</td><td></td><td>MAE0004 2</td><td></td><td></td></tr><tr><td>a. External patching switching and With Host base and or mobile systems . interface functions (4.1.3.5.1)</td><td></td><td></td><td>MAE0004 3</td><td>N/A</td><td></td></tr><tr><td>b. Interface functions (4.1.3.5.2)</td><td>With external hosts to exchange video . / digital imagery digital data.</td><td></td><td>MAE0004 4</td><td>YES</td><td></td></tr><tr><td></td><td>1. &gt;/= secret level via Trojan Spirit II.</td><td></td><td>MAE0004 5</td><td>YES</td><td></td></tr><tr><td></td><td>2. @ class / unclass to host provided . COMMS systems</td><td></td><td>MAE0004 6</td><td>N/A</td><td></td></tr><tr><td></td><td>3. @ class / unclass to associated . shelters</td><td></td><td>MAE0004 7</td><td>YES</td><td></td></tr><tr><td>c. Phone Systems (4.1.3.5.3)</td><td>both Red and Black capability</td><td>utilize instrument</td><td>single MAE0004 8</td><td>YES</td><td>MAE0013 YES 8</td></tr><tr><td colspan="6">TCS Block 0</td></tr><tr><td>Version 2.0 Capabilities and Characteristics</td><td>Thresholds</td><td>Objectives</td><td>TCS RQMT</td><td>TCS ORD Compatibl RQMT</td><td>2/12/99 TCS</td><td>TCS OI</td></tr><tr><td rowspan="3"></td><td></td><td></td><td>TRACIN G</td><td>Threshold</td><td>e With TRACIN G</td><td>Compati with Objecti</td></tr><tr><td></td><td></td><td>NUMBER</td><td></td><td>NUMBE R</td><td></td></tr><tr><td>4 phone lines</td><td></td><td>MAE0004 9</td><td>N/A</td><td></td><td></td></tr><tr><td></td><td>1. Full duplex voice COMMS</td><td></td><td>MAE0005 0</td><td>N/A</td><td></td><td></td></tr><tr><td></td><td>2. Phone lines accessed through. individual instruments</td><td></td><td>MAE0005 1</td><td>N/A</td><td></td><td></td></tr><tr><td></td><td>3. Support internal COMMS</td><td></td><td>MAE0005 2</td><td>YES</td><td></td><td></td></tr><tr><td></td><td>4. Phone not accessed through.</td><td></td><td>MAE0005 3</td><td>N/A</td><td></td><td></td></tr><tr><td>e. Comm status display</td><td>intercom / radio Monitor all incoming and outgoing .</td><td></td><td>MAE0005 4</td><td>N/A</td><td></td><td></td></tr><tr><td>f. Interface connectivity (4.1.3.5.4)</td><td>data To user</td><td>To remote Defense MAE0005 Message System</td><td>5</td><td>YES</td><td>MAE0013 9</td><td>YES</td></tr><tr><td></td><td></td><td>terminals secondary</td><td>&amp; NITF</td><td></td><td></td><td></td></tr><tr><td>g. Data transmitted</td><td>Via Combat Intelligence System (CIS) .</td><td>servers</td><td>MAE0005 6</td><td>NO</td><td></td><td></td></tr><tr><td colspan="2">Capabilities and Characteristics</td><td>Thresholds</td><td>Objectives</td><td>TCS RQMT TRACIN G</td><td>TCS ORD Compatibl RQMT e With TRACIN Threshold</td><td>TCS TCS OI Compati with G Objecti</td></tr><tr><td colspan="2">3.8 Exploitation System (4.1.4.1) - CIGSS Compliant 300 images a day</td><td>450 images</td><td>NUMBER MAE0005</td><td>N/A</td><td>NUMBE R MAE0014</td><td>N/A</td></tr><tr><td>Multi-Source Intelligence Ground System (MIGS)</td><td></td><td></td><td>7</td><td></td><td>0</td><td></td></tr><tr><td>a. Exploit b. Mobility</td><td>In transient cases</td><td></td><td>MAE0005</td><td>N/A</td><td></td><td></td></tr><tr><td>c. Capabilities</td><td>- Ephemeral data read by eye</td><td></td><td>8 MAE0005</td><td>N/A</td><td></td><td></td></tr><tr><td></td><td>- Reference imagery</td><td></td><td>9 MAE0006</td><td>N/A</td><td></td><td></td></tr><tr><td></td><td>- Real time roam</td><td></td><td>0 MAE0006</td><td>N/A</td><td></td><td></td></tr><tr><td></td><td>- Display 2 images simultaneously</td><td></td><td>1 MAE0006</td><td>N/A</td><td></td><td></td></tr><tr><td></td><td>- Computer assist object counting</td><td></td><td>2 MAE0006</td><td>N/A</td><td></td><td></td></tr><tr><td></td><td></td><td></td><td>3</td><td></td><td></td><td></td></tr><tr><td></td><td>- Automated hard-copy report</td><td></td><td>MAE0006 4</td><td>N/A</td><td></td><td></td></tr></table>

<table><tr><td colspan="2">Capabilities and Characteristics Thresholds</td><td rowspan="5">Objectives</td><td colspan="3">TCS TCS ORD</td><td colspan="7" rowspan="5">TCS TCS O1 Compati with</td></tr><tr><td></td><td></td><td>RQMT TRACIN G</td><td>Compatibl RQMT e With TRACIN Threshold</td><td colspan="7">G</td></tr><tr><td colspan="3"></td><td>NUMBER</td><td colspan="7">NUMBE R</td></tr><tr><td>- Access to exploitation support .</td><td></td><td>MAE0006 N/A</td><td></td><td colspan="7"></td></tr><tr><td>database - Organically supported</td><td></td><td>5 MAE0006</td><td>N/A</td><td colspan="7"></td></tr><tr><td></td><td>- Single collector</td><td>- Multiple collectors MAE0006</td><td>6</td><td>N/A</td><td>MAE0014</td><td colspan="4">N/A</td></tr><tr><td>4.0 Logistics and Readiness</td><td>Surge / combat sortie rates for 30 days .</td><td></td><td>7 MAE0006</td><td>N/A</td><td>1</td><td colspan="4"></td></tr><tr><td>Combat Support (4.2.1) 4.0.1 Airborne Segment (4.2.1.1)</td><td>50 hrs</td><td>300 hrs</td><td>8 MAE0006</td><td>N/A</td><td></td><td colspan="4">N/A</td></tr><tr><td>a. MTBMP</td><td>Mean Time Between Maintenance -</td><td></td><td>9</td><td></td><td>MAE0014 2</td><td colspan="4"></td></tr><tr><td>b. MRT</td><td>Preventative &lt; 1.9 hrs</td><td>1 Hr</td><td>MAE0007</td><td>N/A</td><td>MAE0014</td><td colspan="4">N/A</td></tr><tr><td>c. MMax</td><td>90% &lt;/= 3.5 hrs</td><td>2.5 hrs</td><td>0 MAE0007</td><td>N/A</td><td>3 MAE0014</td><td colspan="4">N/A</td></tr><tr><td></td><td></td><td></td><td>1</td><td></td><td>4</td><td colspan="4"></td></tr><tr><td>4.0.2 Ground Segment (4.2.1.2) a. MTBMP return to Status</td><td>&lt;/= 30 Min</td><td></td><td>MAE0007 2</td><td>YES</td><td></td><td colspan="4"></td></tr><tr><td rowspan="2">Capabilities and Characteristics</td><td rowspan="2">Thresholds</td><td rowspan="2">Objectives</td><td rowspan="2">TCS RQMT TRACIN G NUMBER</td><td rowspan="2">TCS ORD Compatibl e With TRACIN Threshold</td><td rowspan="2">TCS RQMT G NUMBE R</td><td colspan="4" rowspan="2">TCS OI Compati with Objecti</td></tr><tr><td colspan="3"></td></tr><tr><td>Interference</td><td>&lt;/= 60 Min / week</td><td>&gt;/= 30 Day interval</td><td>MAE0007 3</td><td>YES</td><td>MAE0014 5</td><td colspan="4">YES</td></tr><tr><td>Non interference</td><td>&lt;/= 60 Min / day</td><td></td><td>MAE0007 4</td><td>YES</td><td></td><td colspan="4"></td></tr><tr><td>b. MRT</td><td>&lt; 1.9 hrs</td><td></td><td>MAE0007 5</td><td>YES</td><td></td><td colspan="4"></td></tr><tr><td>c. MMax</td><td>90% &lt;/= 3.5 hrs</td><td></td><td>MAE0007 6</td><td>YES</td><td></td><td colspan="4"></td></tr><tr><td>4.0.3 System (4.2.1.3)</td><td>80%</td><td>95%</td><td>MAE0007 7</td><td>YES</td><td>MAE0014</td><td colspan="4">YES</td></tr><tr><td>a. MC</td><td>Mission Capable</td><td></td><td></td><td></td><td>6</td><td colspan="4"></td></tr><tr><td>b. MTBCF</td><td>40 hrs</td><td></td><td>MAE0007 8</td><td>YES</td><td></td><td colspan="4"></td></tr><tr><td rowspan="3">c. ETOS</td><td>Mean Time between Critical Failures</td><td></td><td>MAE0007</td><td></td><td></td><td colspan="4"></td></tr><tr><td>75%</td><td>85%</td><td>9</td><td>YES</td><td>MAE0014 7</td><td colspan="4">YES</td></tr><tr><td>Effective time On Station</td><td>70%</td><td></td><td></td><td>MAE0014</td><td colspan="4">YES</td></tr><tr><td></td><td>4.0.4 Access for Maintenance (4.2.3) LRI for ease of maintenance access</td><td></td><td>MAE0008 0</td><td>YES</td><td></td><td></td></tr><tr><td>4.0.5 Test Points (4.2.4)</td><td>Provide to connect test equipment</td><td></td><td>MAE0008 1</td><td>YES</td><td></td><td></td></tr><tr><td>4.1 Mobility (4.2.5.1) When stowed an MAE system must</td><td>Flight in C-130 aircraft</td><td>&lt;/= 2 C-141Bs and MAE0008 C-17, C-5, CRAF</td><td>2</td><td>YES</td><td>MAE0014 9</td><td>YES</td></tr><tr><td>be mobile, deployable, and transportable by standard means to</td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>include road and air a. The MAE system must have</td><td>a roll on / off capability</td><td></td><td>MAE0008 3</td><td>YES</td><td></td><td></td></tr><tr><td>b. The MAE system must</td><td>Suffer no internal or external damage . or degradation of performance from</td><td></td><td>MAE0008 4</td><td>YES</td><td></td><td></td></tr><tr><td>c. Tear down or Set up (4.2.5.2)</td><td>transportation by truck or aircraft or as a result of being loaded Within 12 hrs</td><td></td><td>MAE0008</td><td>YES</td><td></td><td></td></tr><tr><td>d. Environmental Control Units Provided (ECU) (4.2.5.3)</td><td></td><td></td><td>5 MAE0008 6</td><td>N/A</td><td></td><td></td></tr><tr><td>Capabilities and Characteristics</td><td>Thresholds</td><td>Objectives</td><td>TCS RQMT TRACIN G NUMBER</td><td>TCS ORD Compatibl e With TRACIN Threshold</td><td>TCS RQMT G NUMBE</td><td>TCS 01 Compati with Objecti</td></tr><tr><td>e. Power Generator / Consumption System remain MC during power . (4.2.5.4)</td><td>surges / sags Autoranging</td><td></td><td>MAE0008 7</td><td>YES</td><td>R</td><td></td></tr><tr><td></td><td>5. Critical System characteristics (4.3) Operated by personnel in CW gear Collect flight level MAE0008</td><td></td><td>MAE0008 8</td><td>YES</td><td></td><td></td></tr><tr><td>a. Operational Environment Survivability</td><td>during launch and recovery</td><td>environmental info: Temp, dew point, altitude, wind speed</td><td>9</td><td>YES</td><td>MAE0015 0</td><td>YES</td></tr><tr><td>MAE System (4.3.2.1)</td><td></td><td>and direction, and relaying info. to the GCS</td><td></td><td></td><td></td><td></td></tr><tr><td>O-Level maintenance</td><td>All maintenance tasks in cool weather . gear</td><td></td><td>MAE0009 0</td><td>YES</td><td></td><td></td></tr><tr><td>b. Shelters designed to: (4.3.2.2)</td><td>- Minimize NBC contamination</td><td>Compatible KMU-450 decontamination units</td><td>with MAE0009 1</td><td>N/A</td><td>MAE0015 1</td><td>N/A</td></tr><tr><td></td><td>- Be painted with chemical agent. resistant, non toxic paint</td><td></td><td>MAE0009 2</td><td>N/A</td><td></td><td></td></tr><tr><td>Capabilities and Characteristics Thresholds</td><td>Objectives</td><td>TCS RQMT TRACIN G NUMBER</td><td>TCS ORD Compatibl RQMT e With TRACIN Threshold</td><td>TCS G NUMBE</td><td colspan="3">TCS OI Compati with Objecti</td></tr><tr><td>- Include space for a Chemical Detection Kit</td><td></td><td>MAE0009 3</td><td>N/A</td><td>R</td><td colspan="3"></td></tr><tr><td>c. Equipment Operation within shelter By personnel in full aircrew ensemble</td><td></td><td>MAE0009 4</td><td>YES</td><td></td><td colspan="3"></td></tr><tr><td>d. Safety (Ground / Airborne - Built in fire suppression equipment Segments)</td><td></td><td>MAE0009 5</td><td>N/A</td><td></td><td colspan="3"></td></tr><tr><td>- Emergency egress and exit lighting</td><td></td><td>MAE0009 6</td><td>N/A</td><td></td><td colspan="3"></td></tr><tr><td>- Emergency power cutoff</td><td></td><td>MAE0009 7</td><td>N/A</td><td></td><td colspan="3"></td></tr><tr><td>- A safe means of egress</td><td></td><td>MAE0009 8</td><td>N/A</td><td></td><td colspan="3"></td></tr><tr><td>e. System designed to protect from internal and external generated . personnel (4.3.3.1) electricity and radiation</td><td></td><td>MAE0009</td><td>YES</td><td></td><td colspan="3"></td></tr><tr><td>With safety interlocks to interrupt . electrical power</td><td></td><td>9 MAE0010 0</td><td>YES</td><td></td><td colspan="3"></td></tr><tr><td rowspan="2">Capabilities and Characteristics</td><td rowspan="2">Thresholds</td><td rowspan="2">Objectives</td><td rowspan="2">TCS RQMT TRACIN G NUMBER</td><td rowspan="2">TCS ORD Compatibl</td><td colspan="3" rowspan="2">TCS TCS 01 RQMT Compati TRACIN G Objecti NUMBE R</td></tr><tr><td colspan="2">e With Threshold</td></tr><tr><td></td><td>Equipment that must be handled moved, installed, etc. shall be designed with human factors and safety in mind</td><td></td><td>MAE0010 1</td><td>YES</td><td colspan="3"></td></tr><tr><td>f. Flight Safety (4.3.3.3) Electronic Protection and War</td><td>System design provide an acceptable mission crew workload</td><td></td><td>MAE0010 2</td><td>YES</td><td colspan="3"></td></tr><tr><td>g. Reserves Mode (WARM) (4.3.4)</td><td></td><td>Detect any jamming</td><td></td><td>MAE0015 2</td><td colspan="3">2</td></tr><tr><td>h. Electromagnetic compatibility Operate within their respective . (4.3.5.1)</td><td>electromagnetic environment</td><td></td><td>MAE0010 3 MAE0010</td><td>YES</td><td colspan="3"></td></tr><tr><td>i. Security (4.3.7.3)</td><td>All cryptological equipment must be. Electronic Key Management System (EKMS) interoperable</td><td></td><td>4</td><td>N/A</td><td colspan="3"></td></tr></table>

## APPENDIX C: CR-TUAV Applicable Capability Criteria and Characteristics

<table><tr><td colspan="1" rowspan="1">CR ORDRQMTTRACE #</td><td colspan="1" rowspan="1">REQUIREMENT DESCRIPTION</td><td colspan="1" rowspan="1">CR ORDTHRESHOLD RQMT</td><td colspan="1" rowspan="1">CR ORDOBJECTIVERQMT</td><td colspan="1" rowspan="1">TCS ORDTHRESHOLDCOMPATIBLE</td><td colspan="1" rowspan="1">TCS ORDOBJECTIVECOMPATIBLE</td></tr><tr><td colspan="1" rowspan="1">CRS0001</td><td colspan="1" rowspan="1">The system will have a minimum of two GCSs, two Ground DataTerminals (GDTs), one Portable Ground Control Station (PGCS)and one Portable Ground Data Terminal (PGDT) with line ofsight (LOS) command and control links to, and receipt fortelemetry and</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0002</td><td colspan="1" rowspan="1">The system will have sufficient AVs to support a wartime surgeOPTEMPO</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0003</td><td colspan="1" rowspan="1">The system will be capable of near real time (NRT) transmissionof Electro Optic/Infrared (EO/IR) imagery</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0004</td><td colspan="1" rowspan="1">The CR-TUAV baseline is capable of 12 hours of continuousoperations within a 24-hour period.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0005</td><td colspan="1" rowspan="1">The system has the capability of surge operations for 18 hourswithin a 24-hour period for no more than three consecutive days,with the following day being limited to eight hours of operations.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0006</td><td colspan="1" rowspan="1">The objective system will be capable of 18 hours of continuousoperations within a 24-hour period with a surge capability of 24hours of 24 hours for a period of 3 days.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0007</td><td colspan="1" rowspan="1">The CR-TUAV system will have an endurance of four hours onstation at 50 kms</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0008</td><td colspan="1" rowspan="1">The CR-TUAV system will have an endurance (3-4 hrs at 200kmobjective).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0009</td><td colspan="1" rowspan="1">The threshold system will carry enough supplies and spares forinitial operations.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0010</td><td colspan="1" rowspan="1">The complete CR-TUAV system will fit in no more than two HighMobility Multipurpose Wheeled Vehicles (HMMWVs) withshelters, two Cargo/Troop carrying HMMWVs, and two trailerswith enough room for all personnel, crew members' combatequipment (rifles,</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0011</td><td colspan="1" rowspan="1">/seven-day period (objective).</td><td colspan="1" rowspan="1">.</td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1">.</td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0012</td><td colspan="1" rowspan="1">A threshold requirement is for a system configurable to deliver72 hours of operational capability at a minimum of 12 flight hourson station in a 24 hour period deployable in a single C-130sortie (using the HMMWV as the prime mover and including</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0013</td><td colspan="1" rowspan="1">The complete baseline CR-TUAV system with personnel andequipment, must be transportable in no more than two C-130sorties.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0014</td><td colspan="1" rowspan="1">OPTEMPO.  The threshold system must be capable of 12continuous hours of operation on station in a 24 hour period;with a surge capability of 18hrs of 24hrs for 72 hour period.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0015</td><td colspan="1" rowspan="1">The objective system will be capable of 18 continuous hours ofoperation on station in a 24 hour period; with the capability ofsurging to 24 hrs of 24 hrs for a 72 hour period.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0016</td><td colspan="1" rowspan="1">The CR-TUAV system shall have a thresholdMean TimeBetween System Abort (MTBSA) of 20 hours;</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0017</td><td colspan="1" rowspan="1">the CR-TUAV system shall have an objective MTBSA of 54hours</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0018</td><td colspan="1" rowspan="1">Weather. The system will operate in all hot and basic (threshold)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0019</td><td colspan="1" rowspan="1">and cold (objective) climatic conditions as defined in the ArmyRegulation for Research, Development, Test, and Evaluation ofMateriel for Extreme Climatic Conditions (AR 70-38).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0020</td><td colspan="1" rowspan="1">Electrical Power. The system's ground components will operatewith standard electrical power available within the Department ofDefense (DOD) family of mobile electric power sources(objective) (i.e. mobile tactical generators)</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0021</td><td colspan="1" rowspan="1">The system must be capable of providing continuous power toavoid loss of all system data or loss of AV control during primepower outages.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0022</td><td colspan="1" rowspan="1">Operators will be able to adapt the system to standard worldwidecommercial alternating current power (120 volts/60 hertz and220 volts/50 hertz)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0023</td><td colspan="1" rowspan="1">Ground Communications.     Ground components must useService standard tactical  communications equipment andprocedures.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0024</td><td colspan="1" rowspan="1">The system shall provide a minimum of 2 Very High Frequency(VHF) radios.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0025</td><td colspan="1" rowspan="1">The system shall be Mobile Subscriber Equipment (MSE)compatible. CR-TUAV communications to include the capabilityto inject moving imagery into the Global Broadcast System(GBS) must interface with selected standard DOD Command,Control, Communication</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0026</td><td colspan="1" rowspan="1">All communications will be interoperable with National SecurityAgency approved encryption systems.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0027</td><td colspan="1" rowspan="1">All real-time video imagery exported to other imagery systemsshall be in the EIA-RS-170 format.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0028</td><td colspan="1" rowspan="1">The system shall have UHF communications (capable of secureoperations during wartime) with Air Traffic Control (ATC)agencies (peacetime) andAWACS and ABCCC aircraft(wartime/exercises).</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0029</td><td colspan="1" rowspan="1">Fuel. The threshold system (AV and generators) must use MotorGasoline (MOGAS) and/or heavy fuel</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0030</td><td colspan="1" rowspan="1">the objective system must use heavy fuel only. (KPP)*</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0031</td><td colspan="1" rowspan="1">On Station Time (Endurance @ Range). A threshold flight onstation time of 4 hours at a 50km range (threshold)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0032</td><td colspan="1" rowspan="1">3-4 hours at a 200 km range (objective) with airborne missionequipment (airborne data relay, MMP, transponder, etc.)included.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0033</td><td colspan="1" rowspan="1">Construction such that components do not exceed the ability of 2people to move them from the prime mover to the launch and/orrecovery site and back to the prime mover. This includes MMPs,data links, and navigation devices necessary to perform all</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0034</td><td colspan="1" rowspan="1">A threshold service ceiling of 4267.2 meters (14,000 ft) MeanSea Level (MSL) on a standard day.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0035</td><td colspan="1" rowspan="1">The AV will have an objective service ceiling of 4,572 metersMSL (I5, 000 ft) on a standard day.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0036</td><td colspan="1" rowspan="1">Autonomous navigation and flight between multiple, selectedway points; the capability of updating or reprogramming waypoints from controlling GCS or Launch and Recovery (L/R)equipment.During flight, the AV must perform automatic loiter(adjustable)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0037</td><td colspan="1" rowspan="1">A non-explosive, self-destruct capability is also a thresholdrequirement.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0038 Th</td><td colspan="1" rowspan="1">e capability to launch and recover in cross-winds from 0 to 20knots and operate in moderate precipitation conditions.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0039</td><td colspan="1" rowspan="1">System design to allow for mission capability throughout a 3 day(72 hours) profile (threshold),</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0040</td><td colspan="1" rowspan="1">|7dayprofile(objective)   per   an   Operational   ModeSummary/Mission Profile (OMS/MP)</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0041</td><td colspan="1" rowspan="1">The threshold capability of sending payload data, magneticheading information, AV-location, and designated targetcoordinates to the CR-TUAV GCS and RVT.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0042</td><td colspan="1" rowspan="1">The AV will have the capability of sending this information to theGCS and RVT of the other UAVs once the systems haveachieved  Tactical   ControlSystem (TCS)   compatibility(objective).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0043</td><td colspan="1" rowspan="1">Navigation   lights  that   comply   with   Federal   AviationAdministrationregulations   and   that   are   capableofactivation/deactivation from GCS/GDTanytimedata link isestablished.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0044</td><td colspan="1" rowspan="1">A threshold loiter airspeed between 60and 75 knots, and athreshold dash speed of at least 90 knots</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0045</td><td colspan="1" rowspan="1">(110 knots objective)</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0046</td><td colspan="1" rowspan="1">A meteorological sensor that measures temperature accurate towithin one degree Celsius, relative humidity (* 2% between 0%and 80% relative humidity and * 3% between 80% and 100%relative humidity), and barometric pressure (* 0.1 inches (3.37millibar)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0047</td><td colspan="1" rowspan="1">Identification Friend or Foe (IFF) Mode IV or the follow-oncombat identification system.       Capable of activation,deactivation, and in-flight update from the controlling GCS.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0048</td><td colspan="1" rowspan="1">A UHF radio/data relay for communications (secure duringwartime) with ATC agencies (peacetime), AWACS and ABCCC(wartime/exercises), and manned aircraft.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0049</td><td colspan="1" rowspan="1">The AV will have sufficient survivability (acoustic, visual, IR, andRadar Cross Section (RCS)) to be able to conduct operationsunder the wartime OPTEMPO without a numerous and costlysupply of attrition AVs (Annex C, System Survivability (S)). The</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0050</td><td colspan="1" rowspan="1">RCS and Infrared (IR)—objective) as stated on page 2-11,System Threat Assessment Report (STAR), 15 September 1995or its' revision.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0051</td><td colspan="1" rowspan="1">The AV will have provisions to accommodate weight, space, andpower for necessary instrumentation to allow tactical trainingoperations at the Combat Training Centers (CTC).Instrumentation includes, but not limited to Multiple Laser TargetEngagement</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0052</td><td colspan="1" rowspan="1">AV will be capable of mission operations during conditions ofmoderate icing (objective).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0053</td><td colspan="1" rowspan="1">will be capable of near-real-time transmission of payload andtelemetry data to Apache and Comanche helicopters and AirForce/Navy Close Air Support (CAS)Aircraft. (objective).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0054</td><td colspan="1" rowspan="1">An initial MMP capable of day/night passive imagery. Whenflying at an operationally effective altitude (&gt;8,000ft AGL—day;and &gt;6,000ft AGL—night) and standoff range 3 km (threshold)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0055</td><td colspan="1" rowspan="1">(5km - objective) from the imaged target, the system must becapable of performing target detection, recognition, and trackingof light wheeled and tracked vehicles and of providing targetinginformation of sufficient accuracy and timeliness to</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0056</td><td colspan="1" rowspan="1">Auto-track is required. In the objective system, the system mustbe capable of performing wide area surveillance and targetclassification and identification.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0057</td><td colspan="1" rowspan="1">(The second priority payload will be the SAR/MTI multi-modeRadar payload See Appendix B to Annex B).   On boardprocessing is required. (objective) (KPP)*</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0058</td><td colspan="1" rowspan="1">Available minimum payload weight capacity shall be not lessthan 60 Ibs (threshold)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0059</td><td colspan="1" rowspan="1">and not less than 100 Ibs (objective).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0060</td><td colspan="1" rowspan="1">Target Location Error (TLE) in terms of Circular Error Probable(CEP) must have a threshold of  *80 meters from anoperationally effective altitude (&gt;8000ft AGL—day; &gt;6000ftAGL—night) and standoff range (3-5km) from the imaged target.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0061</td><td colspan="1" rowspan="1">The objective is 50 meters from an operationally effectivealtitude (&gt;8000ft AGL—day; &gt;6000ft AGL—night) and standoffrange (3-5km) from the imaged target.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0062T</td><td colspan="1" rowspan="1">he objective DL shall be the Tactical Common Data Link(TCDL). The threshold DL must:</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0063|D</td><td colspan="1" rowspan="1">ata Link (DL).     The thresholddatalink will meet therequirements listed below...Provide a line of site data linkcapability from the controlling GCS to AV (and vice versa)without relay from other AVs, satellites, or surface relay.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0064No</td><td colspan="1" rowspan="1">t create mutual interference with other friendly electronicsystems.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0065</td><td colspan="1" rowspan="1">Be capable of simultaneous transmission and reception ofcommand up-link and sensors/AV telemetry downlink usingdiscrete, selectable frequencies (threshold).</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0066</td><td colspan="1" rowspan="1">Be Low Probability of Intercept and Detection (LPI/LPD) andenciphered using NSA approved encryption technologies,methods, and equipment (objective)</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0067</td><td colspan="1" rowspan="1">GDT must be capable of being remoted a minimum of 400meters ... from the GCS.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0068</td><td colspan="1" rowspan="1">(1000 meters objective) from the GCS.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0069</td><td colspan="1" rowspan="1">As a minimum, provide data distribution (imagery) from AV toCR-TUAV GCS/GDT and all RVTs.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0070</td><td colspan="1" rowspan="1">The DL shall also provide data distribution from the CR-TUAVAV to other UAVs' GCSs (and vice versa) once both UAVsystems achieve upgrade to TCS compatibility (objective).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0071|</td><td colspan="1" rowspan="1">As an objective, provide NRT imagery on the move directly toselected Command and Control (C2) nodes, (e.g. BattleCommand Vehicles (BCV), Future Scout Cavalry  System(FSCS), and C2 aircraft), and all RVTs.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0072</td><td colspan="1" rowspan="1">The CR-TUAV GCS will consist of subassemblies that weigh nomore than 100 pounds (45.63 kilograms)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0073</td><td colspan="1" rowspan="1">Have a minimum of three peripheral ports to drive externaldevices.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0074</td><td colspan="1" rowspan="1">Have the capability of entering all doctrinal communicationsnetwork via radios, local area networks (LAN) and/or wire.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0075</td><td colspan="1" rowspan="1">Record, store, and retrieve mission imagery.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0076</td><td colspan="1" rowspan="1">Control at least I AV and MMP.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0077</td><td colspan="1" rowspan="1">Multiple AV/Payload control is an objective.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0078</td><td colspan="1" rowspan="1">The GCS must be capable of:Automated mission planning functions to include basic flightplanning tools. As a minimum these tools will include:</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0079</td><td colspan="1" rowspan="1">Weight and balance take off data calculations.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0080</td><td colspan="1" rowspan="1">Fuel calculations to include a fuel gauge.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0081</td><td colspan="1" rowspan="1">Terrain avoidance warning and minimum reception altitudecalculation for line of sight flights.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0082</td><td colspan="1" rowspan="1">Payload search area information such as; visual acuity rangedue to atmospheric conditions; diurnal transition periods forthermal imagery, and lunar and solar terrainshadowing(objective).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0083</td><td colspan="1" rowspan="1">Be capable of providing point-andclick routeand sensorplanning</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0084</td><td colspan="1" rowspan="1">Program AVs with mission planning data prior to launch.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0085</td><td colspan="1" rowspan="1">Have tools for importing or creating overlays for fire supportcoordination measures, airspace control measures and threats</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0086</td><td colspan="1" rowspan="1">Provide        override       of       payload        and        UAVautomated/preprogrammed inputs and be capable of changingthe mission plan while the air vehicle is airborne.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0087</td><td colspan="1" rowspan="1">Provide a method of displaying UAV signature versus threats,before and during flight.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0088</td><td colspan="1" rowspan="1">The system should be capable of displaying overlays or icons ofknown threat systems and displaying the threat engagementenvelopes and associated radar terrain masking for thosethreats for route planning . This threat picture will be capable of</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0089</td><td colspan="1" rowspan="1">Be capable of downloading mission plans from future missionplanning systems (as required) and be compatible with theAviation Mission Planning System (AMPS).</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0090|Pr</td><td colspan="1" rowspan="1">ovide the capability to record uplink and downlink messagesincluding operator inputs.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0091</td><td colspan="1" rowspan="1">Provide the capability to create and store multiple mission plans</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0092</td><td colspan="1" rowspan="1">Provide the capability to save mission plans for export to othermission planners</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0093</td><td colspan="1" rowspan="1">Provide the capability to use multiple datum formats includingWGS-84, NAD-72,etc.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0094</td><td colspan="1" rowspan="1">Provide the capability to read NIMA map data to create maps formission plans.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0095</td><td colspan="1" rowspan="1">Recording and storage of digitized annotatedfreeze frameimagery and distributing it in National Imagery TransmissionFormat (NITF), Version 2.0.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0096</td><td colspan="1" rowspan="1">Distributing near real-time (NRT) video to selected users(including commercially available television monitors and VCRs)via a minimum of three external ports. Direct annotated videofeed (via supported unit TACLAN/RS-170/RS-232) to ASASRemote Work</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0097</td><td colspan="1" rowspan="1">Handing-off control of an AV from one CR-TUAV GCS orPortable Ground Control Station (PGCS) to another CR-TUAVGCS or PGCS.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0098</td><td colspan="1" rowspan="1">Once the GCS for CR-TUAV is upgraded to TCS standards,hand-off of an AV between the CR TCS and other UAVs' TCS isrequired (objective).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0099</td><td colspan="1" rowspan="1">Providing automatic system safeguards to prevent unsafe flight.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1">.</td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0100</td><td colspan="1" rowspan="1">Capable of launch and recovery of AVs.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0101</td><td colspan="1" rowspan="1">Capable of changing map datum and displaying NRT imagerywith annotation to include date/time group, selectable targetlocation (in both LAT/LNG, MGRS and UTM coordinates) whenin the center field of view, north seeking arrow, AV position andheading.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0102</td><td colspan="1" rowspan="1">Compatible with the TCS Architecture, as defined by the TCSORD, 3 Feb 97 (objective)</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0103|</td><td colspan="1" rowspan="1">Automatic fire adjustment calculations for indirect fire weaponsand Close Air Support (CAS)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">NO</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0104</td><td colspan="1" rowspan="1">The system shall have a Portable Ground Control Station(PGCS). The PGCS will be capable of initial mission planning,preflight of AVs, launch, and recovery of system AVs. The PGCSwill be capable of minimally acceptable iimageryandcommunications/data relay payload control</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0105</td><td colspan="1" rowspan="1">The PGCS will have a Portable Ground Data Terminal (PGDT)able to control AVs out to a range of 30km..</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0106</td><td colspan="1" rowspan="1">(50 km Objective).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0107</td><td colspan="1" rowspan="1">The PGCS will have one secure VHF radio, one small unit radio,and MSE connectivity for communications.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0108</td><td colspan="1" rowspan="1">RVT. The RVT must: (a) Be transportable and able to be set-up(including antenna and cabling) by no more than 2 people. (i.e.each component must not weigh more than 100 Ibs.)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0109</td><td colspan="1" rowspan="1">(b) Be operable by 1 person with less than one-hour training.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0110</td><td colspan="1" rowspan="1">(c)Receive NRT imagery via cable (minimum 50 meters) fromthe antenna.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0111</td><td colspan="1" rowspan="1">(d)Receive direct downlink (with automatic antenna tracking)from the AV when within 50 km (threshold) ... of the AV. AnRVT-like capability is required to be integrated into the BattleCommand Vehicle (BCV), FSCS, Combat Aviation Brigade</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0112</td><td colspan="1" rowspan="1">Receive direct downlink (with automatic antenna tracking) fromthe AV when within ... (100km objective) of the AV.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0113</td><td colspan="1" rowspan="1">(e)and Apache and Comanche helicopter cockpits (objective)</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0114</td><td colspan="1" rowspan="1">(f)RVT operations on the move is the objective.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0115</td><td colspan="1" rowspan="1">(g) Display annotated (same as MPO display in GCS) imageryto the operator, storing imagery (1 hour minimum), and be ableto recall selected segments.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0116</td><td colspan="1" rowspan="1">(h) Display NRT imagery with annotation to include date/timegroup, selectable target location (in LAT/LNG, MGRS and UTMcoordinates) when in the center field of view, north seekingarrow, AV position, and heading.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0117</td><td colspan="1" rowspan="1">(f) Provide standard output port (s) for peripheral devices (i.e.computer printer / monitor devices).</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0118</td><td colspan="1" rowspan="1">(g) The RVT will be TCS level 2 compatible, as defined in theTCS ORD, 3 Feb 97.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0119</td><td colspan="1" rowspan="1">The threshold CR-TUAV system must be capable of AV L/R onan unprepared surface without engineering equipment requiredto prepare or maintain (i.e. without rocks larger than 2" indiameter, trees or stumps higher than 2"; level—less than 5%grade),</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0120</td><td colspan="1" rowspan="1">The PGCSandPGDT must be capableofnormal L/Roperations.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0121</td><td colspan="1" rowspan="1">The objective requirement is for an automatic L/R systemrequiring no External Pilot (EP) to accomplish the requirementsstated in paragraph 4a(12)(a) above. Operators will performbare minimum emergency recovery.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0122</td><td colspan="1" rowspan="1">The system will be capable of achieving a minimum operationalcapability (prepare one AV, set-up GCS and GDT, plan initialand lost link way point, and emplace necessary safetyequipment) and launching an AV, within 60 minutes (threshold)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0123</td><td colspan="1" rowspan="1">of positioning at a preplanned launch site (30 minutes is theobjective).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0124</td><td colspan="1" rowspan="1">A second AV will be assembled and preflighted within a 30minute period following the achievement of the minimumoperational capability just described.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0125</td><td colspan="1" rowspan="1">After the system has achieved the minimum operationalcapability, the time from receipt of mission tasking to AV launchshall not exceed 30 minutes</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0126</td><td colspan="1" rowspan="1">(15 minutes objective).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0127</td><td colspan="1" rowspan="1">After the system has achieved a minimum operational capabilitythe system will be ready for transport in 30 minutes or less.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0128</td><td colspan="1" rowspan="1">Availability. The CR-TUAV system, without augmentation, willachieve an Operational Availability (Ao) of 85*</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0129</td><td colspan="1" rowspan="1">Reliability and Maintainability. The system shall demonstrate aMean Time To Repair (MTTR) of 0.5 hours for AVUM and 2.0hours for AVIM.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0130</td><td colspan="1" rowspan="1">Transportability. The threshold system will allow for the entiresystem to be transported in 2 HMMWV w/shelters, 2 HMMWVtroop transports &amp; 2 trailers. This should provide enough roomfor all personnel, their combat equipment (rifles, helmets,</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0131</td><td colspan="1" rowspan="1">Deployability. The threshold system must be deployable in 2xC-130 and be CH-47 slingable. An additional C-130 may berequired for a HMMWV w/Trailer for the MMF and fuel.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0132</td><td colspan="1" rowspan="1">The objective complete baseline system, personnel, MMF andfuel will be deployable in 2xC-130.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0133</td><td colspan="1" rowspan="1">War reserve modes and electronic protection (electronic countercountermeasures) will be required for the objective system.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0134</td><td colspan="1" rowspan="1">the system threshold bandwidth for the data uplink (GDT to AV)shall be 50 kHz</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0135</td><td colspan="1" rowspan="1">(the objective is 200 kHz)</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td></tr><tr><td colspan="1" rowspan="1">CRS0136</td><td colspan="1" rowspan="1">The downlink (AV to GDT) shall have a minimum bandwidth of18 MHz (threshold).</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0137</td><td colspan="1" rowspan="1">The CR-TUAV system must operate in the radio frequencyspectrum with complete electromagnetic compatibility.Electromagnetic Environmental  Effects  (E3)  operationalconcerns must be addressed.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0138</td><td colspan="1" rowspan="1">The system and support equipment must be compatible withcurrent individual protective equipment and capable of beingoperated, maintained, and re-supplied by personnel in MissionOriented Protective Posture (MOPP) IV (threshold)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0139</td><td colspan="1" rowspan="1">System electronic components do not require nuclear hardening</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0140</td><td colspan="1" rowspan="1">The AV and ground components must be able to withstand themateriel damaging effects of NBC contaminants anddecontaminants and be able to be decontaminated to negligiblerisk levels (objective)</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">?</td></tr><tr><td colspan="1" rowspan="1">CRS0141 A</td><td colspan="1" rowspan="1">ll components of the CR-TUAV shall be designed to bemutually compatible with other electric or electronic equipmentwithin the system's expected operational electromagneticlenvironment.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0142</td><td colspan="1" rowspan="1">For all components of the CR-TUAV that intentionally emit orreceive hertzian waves, spectrum supportability within the UnitedStates and with all host nations where the system will deployshall be determined for the life of the system throughthe...(MCEB)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0143</td><td colspan="1" rowspan="1">The Close Range - TUAV shall comply with applicable nationaland international spectrum management policies  andregulations.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0144</td><td colspan="1" rowspan="1">The CR-TUAV will meet the minimum protection requirements ofdetection of intrusion, protection against degradation, ordestruction and restoration of capabilities.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">?</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0145</td><td colspan="1" rowspan="1">Maintenance Planning. Requirements for the TUAV systeminclude modular hardware, transportable terminals, embeddeddiagnostics, LRU technology with replacement of componentsavailable at the lowest level.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0146</td><td colspan="1" rowspan="1">The TUAV system is required to operate using DoD standardheavy fuels, standard power sources, and worldwide commercialpower.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0147</td><td colspan="1" rowspan="1">Support Equipment. Standard tools, TMDE,repair parts,lubricants, and fuels will be used.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0148</td><td colspan="1" rowspan="1">lembedded diagnostics will be utilized to the maximum extentpossible.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0149</td><td colspan="1" rowspan="1">Standard Automated Test Equipment (ATE) is to be used for allmaintenance</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0150</td><td colspan="1" rowspan="1">The CR-TUAV system will carry flight line tools and on boardspares to support a 72 hour Early Entry OPTEMPO</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0151</td><td colspan="1" rowspan="1">The Prescribed Load List (PLL) and the Authorized StockageList (ASL) will be located on the MMF and at the Forward DirectSupport Unit (FSU)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0152</td><td colspan="1" rowspan="1">The use of Interactive Electronic Technical Manuals (IETMs) willbe the platform used to support system diagnostics.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0153</td><td colspan="1" rowspan="1">Embedded Training. The CR-TUAV contractor willincorporateembedded training into their proprietary GCS/PGCS</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">N/A</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0154</td><td colspan="1" rowspan="1">Sustainment Training Devices. The system will provide, for theoperator and maintainer, the capability for incorporation ofembedded/add-oninteractivetraining,withself-pacedinstruction, duplicating UAV flight performance characteristics,</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0155</td><td colspan="1" rowspan="1">(The CR-TUAV system will be compatible with the MultipleUnified Simulation Environment (MUSE) (threshold)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0156</td><td colspan="1" rowspan="1">and the U.S. Army Intelligence and Electronic Warfare TacticalProficiency Trainer (IEWTPT) (objective)).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0157</td><td colspan="1" rowspan="1">Technical Manuals (TMs). All TMs will be verified and validatedprior to initial operational test.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0158</td><td colspan="1" rowspan="1">The GCS should conform with the National Institute for StandardTechnology (NIST) Federal Information Processing Standard(FIPS) Publication 151-2 (POSIX.1) objective)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0159</td><td colspan="1" rowspan="1">The GCS will provide a 50% memory storage capacity overstorage delivered (threshold)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0160</td><td colspan="1" rowspan="1">75% spare memory storage over storage delivered (objective).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0161</td><td colspan="1" rowspan="1">The GCS throughput should not exceed 50% of throughputcapability delivered.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0162</td><td colspan="1" rowspan="1">Throughput should not exceed 25% of throughput capabilitydelivered (objective)</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0163</td><td colspan="1" rowspan="1">The GCSs shall comply with the ASD (C3I) JTA-A.   Thisincludes, but is not limited to, the language, the computer,database, architecture and interoperability (threshold).</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0164</td><td colspan="1" rowspan="1">Computer resources shall be Year 2000 compliant.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0165</td><td colspan="1" rowspan="1">GCS must be compatible with the Joint Technical Architecture-Aviation (JTA-A), the Army Battle Command System (ABCS),and Force XXI Battle Command-Brigade and Below (FBCB2).</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0166</td><td colspan="1" rowspan="1">Digital information will be transmitted and received by the GCSIAW the Variable Message Format (VMF) Interface DesignPlan—Test Edition (TIPD-TE)</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0167</td><td colspan="1" rowspan="1">CR-TUAV live imagery payload data will be passed from theGCS to the collocated JSTARS GSM/CGS.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0168</td><td colspan="1" rowspan="1">As an Objective, TUAV live imagery payload data will be passeddirectly from the AV to the JSTARS GSM/CGS.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0169</td><td colspan="1" rowspan="1">Be capable of connectivity for real time imagery (United StatesImagery and Geospatial System ((USIGS)) compatible) to theU.S. Army Common Ground Station (CGS) (threshold—groundconnection;</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0170</td><td colspan="1" rowspan="1">objective direct from any AV).</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0171</td><td colspan="1" rowspan="1">Be capable of passing NRT annotated moving video to theASAS RWS. (KPP)*</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0172</td><td colspan="1" rowspan="1">MIL-STD-188-220, Interoperable Standard for Digital MessageTransfer Device Subsystems. and Joint Publications 6-04 and 3-56.24, U.S. Message Text Formats</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0173</td><td colspan="1" rowspan="1">The CR-TUAV system will be able to use sea, ground, and/or airtransportation. Each component of the system will be airtransportable by helicopter (CH-47/CH-53D)(sling load) anddrive-on/drive-off capable from C-130 aircraft.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0174|</td><td colspan="1" rowspan="1">The threshold time for the system to be configured for sea,ground, or air transport is 2 hours or less.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0175</td><td colspan="1" rowspan="1">The objective time for the system to be configured for sea,ground, or air transport is I hour or less.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td></tr><tr><td colspan="1" rowspan="1">CRS0176|</td><td colspan="1" rowspan="1">The threshold time for the system to be de-configured fromsea/ground/air transport and be ground-mobile is 1 hour or less</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0177 T</td><td colspan="1" rowspan="1">he CR-TUAV system will adhere to regulations and policygoverning military standards for logistics, tools, and othersupport items.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0178</td><td colspan="1" rowspan="1">System(s) fielded to satisfy the requirements for the CR-TUAVmust comply with applicable information technology standards inthe DOD Technical Architecture Framework for InformationManagement (TAEIM).</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0179</td><td colspan="1" rowspan="1">The CR-TUAV will produce sharable, usable, and interoperabledata, per DOD Directive 8320.1 (Data Administration).</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">?</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0180Int</td><td colspan="1" rowspan="1">eroperability with other UAV systems is required.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0181</td><td colspan="1" rowspan="1">Compatibility with the TCS Architecture is required (objective)</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Objective</td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0182Ma</td><td colspan="1" rowspan="1">pping, Charting, and Geodesy Support. The system willutilize Defense Mapping Agency Digital Terrain Elevation Data(DTED), Digital Feature Analysis Data (DFAD), and scannedhard copy maps via optical media.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">CRS0183 Th</td><td colspan="1" rowspan="1">e system will be capable of importing map information vialoperator procedures.</td><td colspan="1" rowspan="1">Threshold</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">YES</td><td colspan="1" rowspan="1"></td></tr></table>