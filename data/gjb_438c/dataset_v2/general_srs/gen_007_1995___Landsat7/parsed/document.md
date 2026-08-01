LPS SRS - Rev 1

560-8SWR/0195

# Landsat 7 Processing System (LPS) Software Requirements Specification

April 28, 1995

GODDARD SPACE FLIGHT CENTER GREENBELT, MARYLAND

# Landsat 7 Processing System (LPS) Software Requirements Specification

April 28, 1995

Prepared by:

Approved by:

Jeff Hosler D   
Software Manager   
Landsat 7 Processing System   
Code 563.2   
Goddard Space Flight Center

ate

Concurred by:

J. B. Martin   
Ground System Manager   
Landsat 7 System   
Code 502   
Goddard Space Flight Center

Date

Joy Henegar Date   
Project Manager   
Landsat 7 Processing System   
Code 563.1   
Goddard Space Flight Center

Dennis M. Giblin Date Chairman, Code 560 CCB Goddard Space Flight Center

R. Obenschain Date   
Project Manager   
Landsat 7 System   
Code 430   
Goddard Space Flight Center

## Abstract

The Landsat 7 Processing System (LPS) provides Landsat 7 data receipt and processing support to the Landsat 7 program, in conjunction with the Earth Science Mission Operations (ESMO) Project. The LPS receives raw wideband data from the Landsat 7 Ground Station, located at the EROS Data Center (EDC), processes it into Level 0R, browse and metadata files, and provides them to the Landsat Processes Distributed Active Archive Center (LP DAAC), also located at the EDC. The software requirements presented in this document are based on the information contained in the LPS Functional and Performance Specification (F&PS), the LPS System Design Specification, and the LPS Operations Concept document.

Keywords:

Landsat 7

Landsat 7 Processing System (LPS)

Landsat 7 Ground Station (LGS)

Landsat Processes Distributed Active Archive Center (LP DAAC)

Functional and Performance Specification (F&PS)

Mission Operations and Data Systems Directorate (MO&DSD)

Systems Management Policy (SMP)

Information Processing Division (IPD)

## Preface

This specification contains the software requirements for the LPS. These requirements are based on an analysis of the requirements contained in the LPS Functional and Performance Specification (F&PS), the LPS System Design Specification, and the LPS Operations Concept document. This LPS software requirements specification, once baselined at/after the System Design/Software Requirements Review (SD/SRR) , will be controlled by the IPD (Code 560) configuration control board (CCB) and maintained and updated, as required, by the LPS Project.

This software requirements specification was prepared by:

Landsat 7 Processing System Project

Code 560

Goddard Space Flight Center

Greenbelt, MD 20771

GSFC SEAS

T. Grubb D. Alban

J. Henegar T. Aslam

J. Hosler B. Bacon

E. Lee B. Boyce

R. McIntosh D. Crehan

K. Michael J. Freeman

D. Sames A. Hall

R. Schweiss M. Huang

C. Liu

S. Liu

N. Patel

S. Priest

T. Sawanobori

R. Shea

D. Specht

R. Tingley

## Table of Contents

## Section 1 - Introduction 1-1

1.1 Scope... .1-1   
1.2 Applicable Documents.. .1-1   
1.2.1 Specification Documents. .1-1   
1.2.2 Reference Documents. .1-2   
1.3 Definitions. .1-3   
Section 2 - Software Requirements Definition Process and   
Products 2-1   
2.1 Process ..2-1   
2.2 Products.. ..2-1   
Section 3 - Reusability 3-1   
3.1 Renaissance Building Blocks ..3-1   
3.2 NMOS Project.. ..3-4   
3.3 SEAS Projects. .3-5   
Section 4 - Software Requirements 4-1   
4.1 LPS System Requirements.. ..4-1   
4.1.1 System Overview.. .4-1   
4.1.2 System Functional Overview... ..4-1   
4.1.3 Open Issues.. .4-4   
4.2 Programmatic Requirements. ..4-5   
4.2.1 Development.. .4-5   
4.2.2 Testing...... ..4-6   
4.2.3 Portability. .4-6   
4.3 Operational Requirements... .4-6   
4.3.1 User-System Interface Requirements... .4-6   
4.3.2 Training .... ..4-6   
4.3.3 Maintenance ..4-7   
4.4 Raw Data Capture Subsystem (RDCS). ..4-8   
4.4.1 Functional Requirements ..4-8   
4.4.1.1 Major Functions.. ...4-8   
4.4.1.2 Interface Requirements. ..4-11   
4.4.1.3 Detailed Functional Requirement ..4-12   
4.4.2 Performance Requirements . ..4-20   
4.5 Raw Data Processing Subsystem (RDPS). ..4-22   
4.5.1 Functional Requirements ..4-22   
4.5.1.1 Major Functions.. ..4-23   
4.5.1.2 Interface Requirements. ..4-27   
4.5.1.3 Detailed Functional Requirements .4-28   
4.5.2 Performance Requirements .4-45   
4.6 Major Frame Processing Subsystem (MFPS). .4-46   
4.6.1 Functional Requirements ..4-46   
4.6.1.1 Major Functions.. ..4-46   
4.6.1.2 Interface Requirements. .4-52   
4.6.1.3 Detailed Functional Requirements .4-53   
4.6.2 Performance Requirements ..4-80   
4.7 Payload Correction Data Subsystem (PCDS) ..4-81   
4.7.1 Functional Requirements ..4-81   
4.7.1.1 Major Functions.. .4-81   
4.7.1.2 Interface Requirements. .4-87   
4.7.1.3 Detailed Functional Requirements . ..4-88   
4.7.2 Performance Requirements ..4-112   
4.8 Image Data Processing Subsystem (IDPS) ..4-113   
4.8.1 Functional Requirements ..4-113   
4.8.1.1 Major Functions. .4-113   
4.8.1.2 Interface Requirements.. ..4-117   
4.8.1.3 Detailed Functional Requirements ...4-118   
4.8.2 Performance Requirements ...4-131   
4.9 Management and Control Subsystem (MACS) ..4-132   
4.9.1 Functional Requirements . ...4-132   
4.9.1.1 Major Functions.. ..4-132   
4.9.1.2 Interface Requirements. .4-135   
4.9.1.3 Detailed Functional Requirements . ...4-137   
4.9.2 Performance Requirements ..4-150   
4.10 LPS Data Transfer Subsystem (LDTS) ..4-152   
4.10.1 Functional Requirements ..4-152   
4.10.1.1 Major Functions.. ..4-153   
4.10.1.2 Interface Requirements.. ..4-155   
4.10.1.3 Detailed Functional Requirements ...4-156   
4.10.2 Performance Requirements ..4-168   
5.0 Database Analysis 5-1   
5.1 Requirement Analysis and Conceptual Design. ..5-3   
5.1.1 Functional Requirement Analysis ..5-3   
5.1.1.1 Raw Data Capture Subsystem (RDCS) ..5-3   
5.1.1.2 Raw Data Processing Subsystem (RDPS)..........5-4   
5.1.1.3 Major Frame Processing Subsystem (MFPS)..5-5   
5.1.1.4 PCD Processing Subsystem (PCDS) .5-6   
5.1.1.5 Image Data Processing Subsystem (IDPS) ......5-6   
5.1.1.6 Management and Control Subsystem (MACS)5-7   
5.1.1.7 LPS Data Transfer Subsystem (LDTS)...............5-7   
5.1.2 Performance Requirement Analysis ..... ....5-8   
5.1.2.1 Response Time.... ...5-8   
5.1.2.2 Reliability, Maintainability, and Availability 5-9   
5.1.2.3 Data Integrity.... ...5-9   
5.1.3 Operational Requirement Analysis.. .5-10   
5.1.3.1 Security.... ..5-10   
5.1.3.2 Backup and Recovery .5-10   
5.1.3.3 Archival and Restoral. .5-11   
5.1.4 Programmatic Requirement Analysis. .5-11   
5.1.5 High Level Entity Relationship Model ..5-11   
5.2 Logical Design. ..5-15   
5.2.1 Logical Schema Definitions. ..5-16   
5.2.2 Functional Usage Analysis.. .5-25   
Section 6 - User Interface (UI) 6-1   
6.1 Task Analysis.. ..6-1   
6.1.1 Drivers.. ..6-1   
6.1.2 Constraints. ..6-2   
6.1.3 Assumptions. ..6-2   
6.1.4 Decisions. ..6-2   
6.1.5 User Interface Event List.... ...6-3   
6.2 User Interface Goals.... ..6-5   
6.3 User Interface Mock-up ...6-5   
6.3.1 Operating System ...6-5   
6.3.2 Reusability... ...6-5   
6.3.3 Oracle Screens. ..6-6   
6.3.3.1 Main Menu ..6-6   
6.3.3.2 Setup Menu. ..6-6   
6.3.3.3 Thresholds and Parameters Menu. ..6-6   
6.3.3.4 Test Menu.. ..6-7   
6.3.3.5 Control Menu. ..6-7   
6.3.3.6 Monitor Menu ...6-8   
6.3.3.7 Files Menu . ...6-8   
6.3.3.8 Reports Menu.. ..6-8   
7.0 LPS Operational Scenarios 7-1   
7.1 Normal Operations ..7-3   
7.1.1 Receive Contact Schedule from the LGS. .7-3   
7.1.2 Receive Parameters from the IAS.. .7-3   
7.1.3 Set Up LPS Strings for Data Capture .7-4   
7.1.4 Receive Data from the LGS ...7-5   
7.1.5 Process Data to Level 0R . ...7-6   
7.1.6 Transfer Files to the LP DAAC ...7-9   
7.1.7 Reprocess LPS Data.. .7-11   
7.1.8 Support Operational Training and Test.. .7-13   
7.2 Contingency Operations ...... ..7-13   
7.2.1 Adjust LPS Level 0R Parameters..... ..7-13   
7.2.2 Adjust LPS Level 0R Thresholds..... ..7-13   
7.2.3 Respond to Failure in LGS/LPS Interface...... ...7-14   
7.2.4 Respond to Failure in LPS/LP-DAAC Interface ...........7-14   
7.2.5 Respond to Exhaustion of LPS Output Storage Capacity7-15..........   
7.2.6 Respond to LPS String Failure.... ..7-15   
Appendix A - Requirements Traceability A-1   
A.1 System to Software Requirements Traceability...........................A-1   
A.2 Software to System Requirements Traceability...........................A-6

## Appendix B - Data Dictionary B-1

Appendix C - WRS Scene Identification Algorithms C-1   
C.1 Algorithms..... ..C-5   
Algorithm #1: WRS Scene Identification..... ..C-5   
Algorithm #2: Longitude and Latitude Algorithm.... ...C-7   
Algorithm #3: Sun azimuth and elevation algorithm ...........C-9   
C.2 Computational Complexity.... ..C-10   
C.3 Estimated DSI... .C-11

## Appendix D - Acronym List D-1

## Section 1 - Introduction

## 1.1 Scope

This document presents the detailed software requirements analysis for the LPS software configuration components. The scope includes the functional, performance, operational, and programmatic requirements of the LPS.

The software requirements analysis is based on the LPS system design, the LPS Functional and Performance Specification (F&PS) and the operations concept, as well as the various technical studies completed by the LPS Project.

This document is part of the LPS project baseline. It takes effect upon approval by the Information Processing Division (Code 560) LPS Project Configuration Control Board (CCB). Proposed changes to this document require the same level of approval.

## 1.2 Applicable Documents

The following documents contain additional details regarding the LPS, the Landsat 7 System and Project, and external systems.

## 1.2.1 Specification Documents

These documents, provide the basis for developing the LPS software requirements presented in this specification.

1. Consultative Committee for Space Data Systems (CCSDS), Recommendation for Space Data System Standards; Advanced Orbiting Systems (AOS), Networks and Data Links: Architectural Specification, Blue Book, CCSDS 701.0-B-1, Issue 1, October 1989

2. NASA GSFC/MO&DSD, Landsat 7 Processing System (LPS) Functional and Performance Specification, Working Draft, 560- 8FPS/0194, December 13, 1994.

3. Martin Marietta Astro Space (MMAS), Landsat 7 System Data Format Control Book (DFCB), Revision A, Volume 4 - Wideband Data, 23007702, December 2, 1994.

4. NASA GSFC, Interface Control Document (ICD) between the Landsat 7 Ground Station (LGS) and the Landsat 7 Processing System (LPS), September 1994.

5. NASA GSFC, Interface Control Document between the EOSDIS Core System (ECS) and the Landsat 7 System, Working Draft, 194- 219-SE1-003, August 1994. [Note: includes LPS-LP DAAC interface requirements].

6. NASA GSFC, Operational Agreement between the Landsat 7 Processing System and the Mission Operations Center (MOC), 1995 (TBD).

7. NASA GSFC, Interface Control Document between the Landsat 7 Processing System and the Image Analysis System (IAS), 23007630, 1994.

8. Computer Sciences Corporation, Seas System Development Methodology, July 1989.

10. NASA GSFC/MO&DSD, Landsat 7 Processing System (LPS) Operations Concept, Draft, 560-3OCD/0194, December 28, 1994.

## 1.2.2 Reference Documents

These documents are used as sources of additional and background information, as required, for developing the LPS software requirements.

1. GSFC/MO&DSD, Systems Management Policy, MDOD-8YMP/0485, July 1986.

2. National Aeronautics and Space Administration (NASA) Goddard Space Flight Center (GSFC) Landsat 7 System Specification, Review issue, 430-L-000-2-A, August 1994

3. NASA GSFC, Landsat 7 Ground Station (LGS) Functional and Performance Specification, Volume 1, Revision 1.0, November, 1994

4. NASA GSFC, Landsat 7 Ground Station (LGS) Operations Concept, 531-OCD-GS/Landsat 7, November, 1994

5. Martin Marietta Astro Space, Landsat 7 Image Assessment System (IAS) Operations Concept, Landsat 7 Library No. 5527, September, 1994

6. National Aeronautics and Space Administration (NASA) Landsat 7 Level 1 Requirements, Draft Issue, August 8, 1994.

7. United States Geological Survey (USGS)/National Oceanic and Atmospheric Administration (NOAA), Index to Landsat Worldwide Reference System (WRS) Landsats 1, 2, 3, and 4, 1982

8. Martin Marietta Astro Space, Landsat 7 System Program Coordinates System Standard, proposed update draft, 23007610A, August 1994.

9. NASA GSFC, LPS Software Management Plan, August 1994.

10. NASA GSFC, Landsat 7 Detailed Mission Requirements, January, 1995.

11. NASA GSFC, Landsat 7 System and Operations Concept (Pre-CCB Baseline version), 430-11-06--003-0, , October 1994.

12. SEAS (D. Crehan, R. McIntosh), WRS Scene Identification Algorithms (DRAFT), February 1, 1995.

13. Mission Operations and Data Systems Engineering, Renaissance Catalog of Building Blocks (Preliminary Draft), January 26, 1995.

## 1.3 Definitions

The following terms, as defined in this section, are commonly used throughout this document to describe the LPS operations concept.

## 1. Landsat 7 Contact Period:

The time duration between the start and end of a wideband data transmissions from the Landsat 7 spacecraft to a ground station. Figure 1-1 illustrates the Landsat 7 contact period concept.

## 2. Interval:

The time duration between the start and stop of an imaging operation (observation) of the Landsat 7 ETM+ instrument.

## 3. Subinterval:

A segment of raw wideband data interval received during a Landsat 7 contact period. Subintervals are caused by breaks in the wideband data stream due to communication dropouts and/or the inability of the spacecraft to transmit a complete observation (interval) within a single Landsat 7 contact period. The largest possible subinterval can be as long as a full imaging interval. The smallest possible subinterval can be as small as one full ETM+ scene with a time duration of approximately 24 seconds. Figure 1-1 illustrates the relationship between satellite on/off periods and satellite/ground contact periods.

## 4. Level 0R Files:

The reformatted, unrectified subinterval data having a sequence of pixels which are spatially consistent with the ground coverage and appended with radiometric calibration, attitude, and ephemeris data. Figure 1-2 illustrates the relationship of LPS files to the received subintervals.

## Level 0R Instrument Data File:

Each file contains the image data from a single band in a single subinterval. The data is grouped by detectors, i.e., for a given major frame, detector 1 data is followed by detector 2 data etc. Reverse scan samples are changed to forward order. This data is nominally aligned using fixed and predetermined integer values that provide alignment for band offset, even/odd detectors, and forward and reverse scans. Quality indicators are appended for each major frame (TBR).

## Calibration File:

One file is created for each subinterval. This file contains all of the calibration data received on a major frame basis for a given subinterval. This is the data received after the Scan Line Data (which follows the End of Line Code) and before the next major frame sync, as described in Applicable Document 3. The data is grouped by detectors, i.e., for a given major frame, detector 1 data is followed by detector 2 data etc. Reverse scans are reversed. The spacecraft time of the major frame corre sponding to this data is appended, as well as the status data.

![](images/e04fdbfed2beb6858c7a50c0df66fbad81013c71e3ab4ce35f96e6b978f31ab3.jpg)

Intervals Mapped to Ground Contacts  
![](images/4711cdf7aa7f8d4aa91bc0e487062a419f15fbe39d26c4630f90e9edde9308a5.jpg)  
FIGURE 1-1: Landsat 7 Contact Periods Concept

## LPS Wideband Data (Inputs)

![](images/0bb144020b3eceac4a2fdb5404ce8e91c06e70e6c20e5f6962b7c2846f546616.jpg)

## LPS Files (Outputs)

a. Level 0R Files:

\- Image Data

\- Cal Data

\- PCD

\- MSCD

b. Browse Data

c. Metadata

\- L0R Q&A Data

Notes:

Cal: Calibration

L0R: Level 0R

MSCD: Mirror Scan Correction Data

PCD: Payload Correction Data

Q&A: Quality and Accounting

Figure 1-2: LPS Files for Landsat 7 Contact Period 3

## Mirror Scan Correction Data (MSCD):

One file is created for each subinterval. This file contains the Scan Line Data extracted from the two minor frames following the End of Line Code in each major frame of the subinterval. The Scan Line Data includes the first half scan error (FHS ERR), the second half scan error (SHS ERR), and the Scan direction (SCN DIR) information. The spacecraft time of the major frame corresponding to this data is appended.

## Payload Correction Data (PCD):

One file created for each subinterval. This file contains the PCD major frames received during a subinterval on a full PCD cycle basis. Quality indicators will be appended on a minor frame basis.

## 5. Browse Image File:

A reduced data volume file of the Level 0R data which can be viewed to determine general ground area coverage and spatial relationships between ground area coverage and cloud coverage. This file contains reduced resolution scenes of the full resolution scene data contained in the Level 0R instrument data files of a subinterval.

## Monochrome Browse:

Contains browse image data for a single band.

## Multi-band Browse:

Contains browse image data from 3 predefined bands of the ETM+ Format 1 scene data.

## 6. Metadata:

One metadata file is created for each subinterval per string. The metadata contains information on the Level 0R data provided in the subinterval, and the names of the Level 0R instrument data, calibration data, PCD, MSCD, and browse image files associated with the subinterval. Metadata also contains quality and accounting information on the return link wideband data used in generating the Level 0R file(s). In addition, metadata includes quality and accounting information on received and processed PCD, and cloud cover assessment for the Worldwide Reference System (WRS) scene contained in the subinterval. The metadata is used to determine the subinterval and/or WRS scene level quality of the Level 0R data stored in the LP DAAC archive.

## 7. Return Link Quality and Accounting Data:

The data quality and accounting information collected by LPS from CCSDS AOS Grade 3 and Bose-Chaudhuri-Hocquenghem (BCH) error detection and correction processing of the raw wideband data received from LGS on a Landsat 7 contact period basis.

## 8. Level 0R Quality and Accounting Data:

The data quality and accounting information collected by the LPS, on a subinterval basis, from processing of the ETM+ major frames constructed from the wideband Virtual Channel Data Units (VCDUs) received during a Landsat 7 contact period.

# Section 2 - Software Requirements Definition Process and Products

## 2.1 Process

The LPS software requirements analysis has been developed using the SEAS System Development Methodology (described in Applicable Document 8) tailored to suit the LPS project environment. The LPS software requirements analysis has been accomplished by performing the following major activities:

a. Development and analysis of an LPS software architecture that is based on LPS structured analysis, conforms to the selected hardware configuration and constraints, and maximizes the use of COTS items in its design.

b. Analysis of the LPS database which is based on the development of a conceptual and logical model of the LPS data.

c. Analysis of a user interface for the LPS, based on functional requirements and operations concepts.

d. Analysis of the LPS system requirements using a CASE tool, Cadre/Teamwork, which supports the structured analysis methodology.

e. Identification of LPS issues which, when resolved, may impact the LPS preliminary design.

## 2.2 Products

Several products are produced as a result of the Software Requirements analysis phase of the LPS. A model of the LPS exists in the Cadre/Teamwork CASE tool. This model includes data flow diagrams, p-specs (functional specifications), a data dictionary, and an entity relationship diagram for the LPS.

# Section 3 - Reusability

## 3.1 Renaissance Building Blocks

There is a pool of software that has already been developed and may be reused for the LPS. By identifying candidate software components, there is the potential to save time, money, and improve an existing component (instead of developing a component).

The following is a list of candidates for reuse. Included are Renaissance Building Blocks and other MO&DSD projects. These candidates will be further investigated during the Preliminary Design Phase of the LPS.

1. The Packet Extractor/Server (building block #RT-EX-05) removes the data unit zone (preferably a CCSDS packet structure versus a mission unique structure ) of a CCSDS frame. Routes selected packets and quality annotations to its clients.

2. The Telemetry VCDU Statistics (building block #RT-EX-06) keeps reception statistics on all CCSDS AOS telemetry VCDUs received. It also extracts CLCW information from real-time VCDUs and maintains this information for use by commanding building blocks.

3. The Event Logger (building block #RT-HS-01) receives event messages from all RT elements, time stamps them and logs them into a history file; provides an event server function that streams event messages to client processes based on specified filter parameters.

4. The History Logger (building block #RT-HS-02) logs annotated spacecraft telemetry frames and packets, command blocks, command echo blocks, NCC blocks, and DSN monitor blocks to the history DBM. A header record is written to the log for each data block to ensure rapid access of data during replays and browsing.

5. The History Replay (building block #RT-HS-03) replays frame and packet history files back into the real-time data path so that real-time processing of the data can be repeated. While replaying frames, the output is sent to either the Packet Extractor/Server (CCSDS missions) or directly to Telemetry

Decommutation (TDM missions). Packets are always replayed directly to Telemetry Decommutation.

6. The Generic Equation Processor (building block #RT-TM-07) uses standard algebraic and trigonometric functions, derives values from the telemetry on the data server, and places the results back on the data server.

7. The Real-Time Attitude Determination (building block #RT-TM-08) processes real-time attitude sensor telemetry data to estimate the current spacecraft attitude using a Kalman filter and/or a single frame method. The system is flexible in terms of the sensor and dynamic models used as well as which state parameters are estimated.

8. The Reports (building block #RT-US-05) generates ASCII report files using data from real-time elements. It processes page snaps, sequential prints, event dumps, telemetry frame dumps, and telemetry packet dumps to an ASCII file, laser printer, or terminal emulator window.

9. The Event Printer (building block #RT-US-06) receives events from the event logger building block in real-time and writes them to a dedicated line (events) printer.

10. The Data Distribution (building block #OL-DM-01) provides the capabilities for cataloging and distributing data products.

11. The Data Reception (building block #OL-DM-02) provides a method for receiving files from external interfaces. This software element polls a specified directory for new files at a user specified interval. When a new file is received, the poller: a) determines the file type and moves the file to a storage directory, b) updates the offline event log, c) executes a script if further processing is required.

12. The File Services (building block #OL-DM-05) provides the capability for backup storage and retrieval and archival storage, retrieval, and access control of data files. The File Server Building Block backs up active, online data file, recovers files from backup media after data loss, transfers online data files to archival storage after a predetermined amount of time and provides access to archived data files by authorized applications and users.

13. The Events Browser (building block #OL-DP-02) allows realtime and logged events information to be queried and displayed according to several different filtering criteria. A graphical "timeline" view of event occurrences by type is provided along with the traditional scrolling text window of event messages.

14. The Data Browser and Editor (building block #OL-DP-03) provides the capability to perform formatted hexadecimal octal, decimal, and ASCII dumps of all history data (e.g. transfer frame logs, packet logs, command blocks, command echo blocks, NCC blocks, DSN monitor blocks) and level zero data sets. Dumps can be viewed on screen or can be routed to a disk or printer. Errors and missing data can be identified. Logged frames and packets can be edited for re-processing by the LZP function. Another feature of the Data Browser and Editor is that it can display the availability of history data of different types within the time range selected.

15. The TDM Processor (building block #OL-DP-06) provides counts of minor, major and incomplete major frames on a per-pass basis.

16. The Attitude Sensor Alignment and Calibration (building block #OL-SD-01) processes attitude history and attitude sensor telemetry data to estimate sensor alignment and calibration parameters using a batch filter algorithm. The system is flexible in terms of the sensor and dynamic models used as well as which state parameters are estimated.

17. The Non-Real-Time Attitude Determination (building block #OL-SD-02) processes attitude sensor telemetry data offline to estimate the spacecraft attitude at a chosen epoch. In addition, the attitude may be propagated in either direction from the chosen epoch using a user-specified data parameter. The epoch attitude may be estimated by one of several methods including batch least-squares or Kalman filter. The software is flexible in terms of the sensor and dynamic models used. Displays of uncertainties and residuals are provided so that the user may easily ascertain the validity of the solution.

18. The State Parameter Validation (building block #OL-SD-04) processes telemetry data to validate onboard computed parameters including, but not limited to, gimbal angles, spacecraft attitude, orbit information, calibration parameters, and start observations. Statistics are computed including mean difference, RMS residuals, and standard deviation.

19. The Attitude Measuring Processing (building block #OL-SD-05) processes converted telemetry data to obtain sensor and actuator measurements adjusted for misalignment and bias in a user-specified reference frame. Resulting data include, but are not limited to, magnetic field vectors, spacecraft-to-celestial body vectors, and spacecraft body rates. the system is flexible in terms of data selection, reference frame, and output format.

20. The Session Manager (building block #OL-UI-01) provides the parameter editor capability to create, view, and modify data associated with an application. Also provides the Sequence Editor capability to sequentially execute a series of related applications.

21. The Display builder (building block #OL-OU-02) allows the construction of new Motif graphical user interfaces (GUIs). The builder takes widgets from both the Motif library and user or project-specific libraries and puts these screen objects onto a palette. From the palette these objects can be dragged to the interface that is under construction. All attributes of the screen objects can be modified before the file is saved as an industrystandard user interface language (UIL) file. Also note that the preferred method for incorporating user-defined widgets into this tool is through an industry-standard Widget Meta Language definition.

22. The Network Time Source (building block #F-TS-01) is hardware and associated device level software and other related utilities used to provide synchronization to an external timing constant. Examples are various UTC boards, NASA-36 boards, or WWV short wave boards and antenna. Provides the interface to the required external timing source.

23. The Network Time Server (building block # F-TS-02) provides the authoritative source(s) of accurate network time for all other workstations and file servers. Typically includes the machine that incorporates the Network Timer Source interface. Also serves as a relay between the Network Timer Source and all other workstations and file servers so that each of these does not require an external interface.

24. The Network Time Client (building block #F-TS-03) queries the Network Timer Server for accurate network timing that is synchronized to the Network Timer Source.

## 3.2 NMOS Project

1. The Distributed Process Control Program (DPCP), of the Ground Operations Technology Testbed, tool enables an operator to start a set of related processes running on one or more host computers. The sequence of steps and process dependencies is entered through use of a table that the operator sets up for the system. The DPCP, when instructed to do so, starts all of the processes on their indicated machines in the proper order. In this way, the correct sequence of startups is consistently maintained and is executable each time the system is started. the DPCP also continues to monitor each process and presents the status information to the operator on a graphical display, showing alert status when a process has died. The DPCP allows the operator to stop all the processes with a single command. This package is completely non-intrusive in that it does not need to be compiled or linked with any of the LPS software.

## 3.3 SEAS Projects

1. Data transfer software can be reused from the Pacor II and DDF projects. Both of these projects perform data transfer, deal with data availability notices, and use inter-process communication to accomplish the data transfers.

2. The Distributed Application Monitor Tool (DAMT), of the Ground Operations Technology Testbed (Code 520), is helpful in analyzing performance of a software system. The DAMT may be used to monitor process on another machine, but the DAMT code must be compiled and/or linked with the application code. The DAMT is currently unable to monitor processes with the same name on different machines in the same network.

3. The user interface portion (called the Integrator) of the Centralized Information System (CIS) for the Spacelab Data Processing Facility may be reused. The Integrator is a simple display which shows the status of pipeline processes and has a window that allows the operator to easily monitor system activities. This is a C/UNIX based application that is portable.

4. The message logging portion of the Centralized Information System (CIS) for the Spacelab Data Processing Facility may be reused. This is C/UNIX based code that uses embedded SQL and is a structured and simple way of logging messages to the Integrator (mentioned above).

5. The Flight Dynamics Facility has potential software configuration items (SWCI) that have potential use within the LPS. One SWCI computes the Greenwich Hour Angle from the Julian date. Another SWCI computes the GCI sun vector.

## Section 4 - Software Requirements

This section describes the LPS software requirements. The requirements in this section are intended for LPS software executing on a single string. Overall system performance requirements have been divided down to the string level.

4.1 LPS System Requirements

## 4.1.1 System Overview

The LPS software context level diagram (Figure 4-1) shows the interactions the LPS software has with other LPS ground system components. Raw wideband data is accepted from the LGS, the LPS generates output files, and then the LP DAAC is notified. The LPS operator issues directives to control the processing of the data. An external time source is used by five of the seven LPS subsystems to get current system time.

LPS requirements from the F&PS have been allocated to each LPS subsystem. These requirements have been further divided between operations, hardware, and software. All software allocated have been analyzed to form this software requirements specification.

There are several requirements that apply to all LPS subsystems. Refer to "Requirements Assigned All Subsystems" portion of Appendix A of the LPS System Design Specification.

## 4.1.2 System Functional Overview

The LPS Level 0 DFD diagram (Figure 4-2) shows the internal flow of data between the seven LPS subsystems. The raw data flows into the RDCS where it is captured. The raw data is then sent to the RDPS where all transmission artifacts are removed, leaving spacecraft mission data. This mission data (Ann\_VCDU) is then passed to the MFPS. The MFPS interprets the mission data and passes payload correction data to the PCDS and image data to the IDPS. The MACS accepts accounting information from the processing subsystems and creates a metadata file. When the metadata file is created, LDTS notifies the LP DAAC that the output files are ready for transfer. LP DAAC then is responsible for transferring the files from the LPS to the LP DAAC. Once the files have been transferred, LDTS deletes them from LPS storage.

FIGURE 4-1

LPS Software Context Level Diagram

FIGURE 4-2

LPS Level 0 Diagram

## 4.1.3 Open Issues

There are issues for the LPS project that remain unresolved or in need of clarification. The following issues are concerned with LPS interfaces :

The LGS interface will be either schedule driven or data driven. The LGS has agreed to send the clock time and data only after the detection of bit sync.

An ICD between LP-DAAC and LPS needs to be defined. It has been proposed that the LPS/LP-DAAC interface operate on a separate FDDI connected to a router. LPS is awaiting a response from LP-DAAC. Another ICD concern is the specification of DAN formats.

The interface with the IAS needs to be stated explicitly. The data is presumed to be sent electronically. Some software may need to be written to receive this data.

The following issues concern the LPS subsystems:

The system or subsystem responsible for the aggregation of the I and Q channels needs to be specified.

The DFCB shows a minor frame consisting of mid scan information that needs to be extracted from the major frame. There is no functional requirement associated with this.

• The procedure for aligning calibration data is still unclear.

Partial PCD cycles will be filled using fill values. It is in question whether this was the original intent.

Explicit rules need to be stated regarding the majority vote decision for the PCD minor frame words.

• The following algorithms need to be identified:

1) the PCD horizontal display shift

2) the determination method for the nearest nominal scene center.

3) the interpolation method for the WRS scene id.

• A decision is needed regarding the granularity and formatting of the LPS file outputs to the LP-DAAC in HDF.

• The precision value of the BER is in question.

The following issues concern the LPS database:

Explicit prevention measures for data loss are still unexplained.

Scene\_Id\_Setup and the Sensor\_Alignment\_Info are not finalized because it is not clear what information will be supplied by the IAS.

Data will be stored for 60 days, after which it will be purged. The number of days is in question.

## 4.2 Programmatic Requirements

## 4.2.1 Development

The development environment for the LPS is the same for all SWCIs of the LPS. The goal of the LPS is to develop most functions using software (this includes application software, COTS, GOTS, system software). Doing so will reduce the need for custom hardware and facilitate future upgrades in service capability.

The application software will be developed using C and UNIX on an SGI Challenge series platform. All operating system upgrades must be coordinated with the LPS development team. All compilers and development tools must be upwardly compatible.

The Oracle DBMS COTS package will be used to manage the LPS database, generate reports (when applicable), and manage a user interface.

All government-furnished equipment will remain available to the development team during the design phases of LPS.

The LPS application software will be developed jointly by the LPS NASA developers and the LPS SEAS developers at GSFC. The operational environment will be at the EDC in Sioux Falls, South Dakota.

Since the LPS development staff will differ from the maintenance staff, the software must be developed and documented with this in mind. On-line documentation, such as LPS specific man pages will be supported.

## 4.2.2 Testing

The following summarizes the LPS testing approaches:

• System will be tested before delivering to EDC by LPS project personnel.

• System will be acceptance tested at EDC by EDC personnel.

• Testing at GSFC will include simulated data from GTSIM and spacecraft test data.

• LPS will support the ground system end to end testing.

## 4.2.3 Portability

The LPS application software needs to be upgradeable. For this reason, the application needs to be developed with portability in mind. POSIX compliant code will be written whenever possible. There may be some instances where code is not compliant due to performance requirements. These instances will be clearly documented to facilitate maintenance.

## 4.3 Operational Requirements

The LPS software will support and comply with the general operational requirements for the LPS system.

## 4.3.1 User-System Interface Requirements

The User-System Interface will be prototyped early in the preliminary design phase of the LPS. Sample screens and demonstrations will be provided to EDC personnel during that phase.

See Section 6 for more details.

## 4.3.2 Training

The training of the LPS operations personnel is TBD. Some training will be needed for both operations and maintenance personnel.

## 4.3.3 Maintenance

The maintenance of the LPS software will occur at the EDC by the maintenance personnel. The maintenance personnel are not planned to be the same or any subset of the development personnel.

## 4.4 Raw Data Capture Subsystem (RDCS)

This subsystem is responsible for receiving raw wideband data and placing it in a datastore for RDPS processing. The raw wideband data is also saved on removable media. This subsystem also restages raw wideband data from the removable media to the on-line datastore for later processing. On request, RDCS generates a data receive summary.

## 4.4.1 Functional Requirements

The following list summarizes the functional requirements allocated to the RDCS:

• Provide the capability to receive return link wideband data for each contact period.

• To record return link wideband data to removable media.

• To retrieve return link wideband data upon request.

• To generate an LPS wideband data receive summary for each contact period.

• Delete data for a specific contact period.

## 4.4.1.1 Major Functions

RDCS captures a raw data byte stream after it receives the start capture directive from the MACS and outputs this raw wideband data to a datastore for further processing by other subsystems. RDCS creates the Contact\_Id information, stores it in the database, and provides it in RDC\_Capture\_Stat for displaying to the operator. A contact summary report is generated upon receipt of a directive from MACS which includes the data set identifier.

RDCS captures a raw data byte stream after it receives the start capture directive from the MACS and outputs this raw wideband data to a datastore for further processing by other subsystems. RDCS creates the Contact\_Id information and notifies the MACS after a contact period ends. A contact summary report is generated upon receipt of a directive from MACS which includes the data set identifier.

Saving of the captured raw wideband data begins after receiving a MACS directive to start the recording to the removable media. When a request for restaging of a contact period data set is issued by the MACS, the requested data set is recovered from the removable media to the on-line store.

When a MACS directive is received requesting a data receive summary, a report is generated describing the data set. The report includes data volume and approximate number of Landsat 7 scenes along with other identifiers.

The major functions of RDCS are depicted in the following data flow diagram.

## 4.4.1.2 Interface Requirements

The following two tables summarize the interface requirements for the RDCS:

Table 4.1 RDCS Interface Requirements - INPUT
<table><tr><td rowspan=1 colspan=1>Input Item Name</td><td rowspan=1 colspan=1>Source</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>Current_Time</td><td rowspan=1 colspan=1>TimeSource</td><td rowspan=1 colspan=1>System wide time source</td></tr><tr><td rowspan=1 colspan=1>Raw_Data_Byte_Stream</td><td rowspan=1 colspan=1>LGS</td><td rowspan=1 colspan=1>Raw data received from LGS viaLPS hardware</td></tr><tr><td rowspan=1 colspan=1>Configuration_ItemMACSS</td><td rowspan=1 colspan=1>store</td><td rowspan=1 colspan=1>LGS_Channel_Id and LPS_ Hard-ware_String_Id from the MACSdatastore</td></tr><tr><td rowspan=1 colspan=1>RDC_Capture_ Drct</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Directive to begin raw datacapture</td></tr><tr><td rowspan=1 colspan=1>RDC_Save_Drct</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Directive to begin saving raw datato removable media</td></tr><tr><td rowspan=1 colspan=1>RDC_Restage_ Drct</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Directive to begin restaging ofraw data from removable media</td></tr><tr><td rowspan=1 colspan=1>RDC_Delete_Drct</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Directive to delete captured rawdata</td></tr><tr><td rowspan=1 colspan=1>RDC_Rpt_DataCapture_Sum_Drct</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Directive to begin generation ofdata receive summary report</td></tr></table>

Table 4.2 RDCS Interface Requirements - OUTPUT
<table><tr><td rowspan=1 colspan=1>Output Item Name</td><td rowspan=1 colspan=1>Destination</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>Raw_WB_Sets</td><td rowspan=1 colspan=1>RDPS</td><td rowspan=1 colspan=1>Raw data to be processed</td></tr><tr><td rowspan=1 colspan=1>Raw_WB_Sets</td><td rowspan=1 colspan=1>Removable_Media</td><td rowspan=1 colspan=1>Raw data saved to short-termstore</td></tr><tr><td rowspan=1 colspan=1>RDC_Capture_Stat</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Return         message         statingdisposition of raw data capture</td></tr><tr><td rowspan=1 colspan=1>RDC_Save_Stat</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Return         message         statingdisposition of raw data save toremovable media</td></tr><tr><td rowspan=1 colspan=1>RDC_Restage_Stat</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Return message stating restage ofRaw_WB_Sets is complete</td></tr><tr><td rowspan=1 colspan=1>RDC_Delete_Stat</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Return         message         statingcompletion of Raw_WB_Sets iscomplete</td></tr><tr><td rowspan=1 colspan=1>RDC_Acct</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Metadata Accounting Information</td></tr><tr><td rowspan=1 colspan=1>Report_RDC_Data_Clapture_Sum</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Accounting information for acontact period</td></tr></table>

## 4.4.1.3 Detailed Functional Requirements

This section contains the process specifications for the lowest level processes in the RDCS data flow diagrams.

NAME: 1.1;14

TITLE: Receive Raw Wideband Data

INPUT/OUTPUT:   
Contact\_Start\_Time : data\_inout   
RDC\_Capture\_Stat : data\_out   
RDC\_Acct : data\_out   
Raw\_WB\_Sets : data\_out   
RDC\_Capture\_Drct : data\_in   
Current\_Time : data\_in   
Raw\_Data\_Byte\_Stream : data\_in   
Configuration\_Items : data\_in

## BODY:

Description of Process This process captures a Raw\_Data\_Byte\_Stream and places it in the Raw\_WB\_Data datastore. It also estimates the number of Megabytes received and places the estimate in the RDC\_Acct datastore.

Assumptions Preconditions None Postconditions None Constraints None

If RDC\_Capture\_Drct is "START", then If there are three contact period data sets in the Raw\_WB\_Sets datastore, then Send as RDC\_Capture\_Stat a message to the MACS indicating that there are already 3 contacts captured. Read Current\_Time to identify Contact\_Start\_Time and output to Contact\_Start\_Time datastore, Start data capture of Raw\_Data\_Byte\_Stream and place the data into the Raw\_WB\_Sets datastore. Send as RDC\_Capture\_Stat a start capture message with Contact\_Start\_Time to the MACS.   
Else if RDC\_Capture\_Drct is "STOP", then Read Current\_Time to identify Contact\_Stop\_Time, Stop data capture, Read Contact\_Start\_Time from the Start\_Time datastore, Calculate RDC\_Acct.Rcv\_Dat\_Vol\_Mbytes from Contact\_Start\_Time and Contact\_Stop\_Time, Set RDC\_Acct.Contact\_Id.LPS\_Hardware\_String\_Id to LPS\_Configuration.LPS\_Hardware\_String\_Id Set RDC\_Acct.Contact\_Id.LGS\_Channel\_Id to to LPS\_Configuration.LGS\_Channel\_Id Set RDC\_Acct.Contact\_Id.Contact\_Start\_Time to Contact\_Start\_Time

Set RDC\_Acct.Contact\_Id.Contact\_Stop\_Time to Contact\_Stop\_Time Send as RDC\_Capture\_Stat a stop capture message with Contact\_Id to the MACS.

Prototype for capturing data can be used.

NAME: 1.2;5

TITLE:Save Raw Wideband Data

INPUT/OUTPUT: Removable\_Media : data\_out RDC\_Save\_Stat : data\_out RDC\_Save\_Drct : data\_in Raw\_WB\_Sets : data\_in

## BODY:

Description of Process This process saves Raw\_WB\_Data to Removable\_Media.

## Assumptions

Preconditions The current contact period Raw\_WB\_Data is in the Raw\_WB\_Sets datastore.

## Postconditions

The current contact period Raw\_WB\_Data has been saved to the Removable\_Media. An RDC\_Save\_Stat has been sent to the MACS.

Constraints None.

## Functional Breakdown

Receives RDC\_Save\_Drct with

RDC\_Save\_Drct.Contact\_Id.LPS\_Hardware\_String\_Id,

RDC\_Save\_Drct.Contact\_Id.LGS\_Channel\_Id,

RDC\_Save\_Drct.Contact\_Id.Contact\_Start\_Time,

RDC\_Save\_Drct.Contact\_Id.Contact\_Stop\_Time.

Reads Raw\_WB\_Data from the Raw\_WB\_Sets datastore.

Output the Raw\_WB\_Data to the Removable\_Media.

Output RDC\_Save\_Stat to the MACS with message that saving is complete.

## Reusability

The system software will be used for the majority of this function.

NAME: 1.3;7

TITLE: Restage Raw Wideband Data

INPUT/OUTPUT: Raw\_WB\_Sets : data\_out RDC\_Restage\_Stat : data\_out RDC\_Acct : data\_out RDC\_Restage\_Drct : data\_in Removable\_Media : data\_in

## BODY:

Description of Process This process extracts Raw\_WB\_Data from the Removable\_Media and places it in the Raw\_WB\_Data datastore per Contact\_Id. It then generates the Contact\_Summary and places it in the RDC\_Acct datastore and sends the RDC\_Restage\_Stat to the MACS.

## Assumptions

Preconditions The correct contact period Removable\_Media item has been mounted.

Postconditions The requested Raw\_Data\_Byte\_Stream has been placed into the Raw\_WB\_Sets datastore. The accounting has been placed in the RDC\_Acct datastore. The RDC\_Restage\_Stat has been sent to the MACS.

Constraints None.

Functional Breakdown Receives RDC\_Restage\_Drct with Contact\_Id.LPS\_Hardware\_String\_Id, Contact\_Id.LGS\_Channel\_Id, Contact\_Id.Contact\_Start\_Time, Contact\_Id.Contact\_Stop\_Time.

If requested data set is not in database then Calculate Rcv\_Dat\_Vol\_Mbytes from the Contact\_Start\_Time and the Contact\_Stop\_Time. Output Contact\_Summary with Contact\_Summary.Rcv\_Dat\_Vol\_Mbytes, Contact\_Summary.Contact\_Id.LPS\_Hardware\_String\_Id, Contact\_Summary.Contact\_Id.LGS\_Channel\_Id, Contact\_Summary.Contact\_Id.Contact\_Start\_Time, and Contact\_Summary.Contact\_Id.Contact\_Stop\_Time

The Raw\_Data\_Byte\_Stream is read from the Removable\_Media and output to the Raw\_WB\_Sets datastore for the specified RDC\_Restage\_Drct. Contact\_Id.   
Output RDC\_Restage\_Stat to the MACS with message that restaging is complete.

Reusability

Most of the software used will be system software.

NAME: 1.4;12

TITLE: Generate Data Receive Summary Report

INPUT/OUTPUT:   
Report\_RDC\_Data\_Capture\_Sum : data\_out RDC\_Acct : data\_in   
RDC\_Rpt\_Data\_Capture\_Sum\_Drct : data\_in   
BODY:   
Description of Process This process generates the Data Receive Summary.

Assumptions Preconditions The RDC\_Acct contains the current or requested Contact\_Summary.

Postconditions The Report\_RDC\_Data\_Capture\_Sum has been generated.

Constraints None.

Functional Breakdown The RDC\_Rpt\_Data\_Capture\_Sum\_Drct with Contact\_Id.LPS\_Hardware\_String\_Id, Contact\_Id.LGS\_Channel\_Id, Contact\_Id,Contact\_Start\_Time and Contact\_Id.Contact\_Stop\_Time is received from the MACS. Calculate approximate number of Landsat scenes by dividing Rcv\_Dat\_Vol\_Mbytes by the number of megabytes per scene. Output Report\_RDC\_Data\_Capture\_Sum to the MACS with Report\_RDC\_Data\_Capture\_Sum.Rcv\_Dat\_L7\_Scenes, Report\_RDC\_Data\_Capture\_Sum.Rcv\_Dat\_Vol\_Mbytes, Report\_RDC\_Data\_Capture\_Sum.Contact\_Id.LPS\_Hardware\_String\_Id, Report\_RDC\_Data\_Capture\_Sum.Contact\_Id.LGS\_Channel\_Id, Report\_RDC\_Data\_Capture\_Sum.Contact\_Id.Contact\_Start\_Time and Report\_RDC\_Data\_Capture\_Sum.Contact\_Id.Contact\_Stop\_Time.

Reusability This function will mostly use COTS software, ORACLE.

NAME: 1.5;4

TITLE: Delete Raw Wideband Data

INPUT/OUTPUT: RDC\_Delete\_Stat : data\_out RDC\_Delete\_Drct : data\_in Raw\_WB\_Sets : data\_in

## BODY:

Description of Process This process deletes the Raw\_Data\_Byte\_Streaam file for a specified contact period.

## Assumptions

econditions The Raw\_Data\_Byte\_Stream file to be deleted exists and has been saved to Removable\_Media.

Postconditions The designated Raw\_Data\_Byte\_Stream file has been deleted.

Constraints None.

Delete Raw\_Data\_Byte\_Stream from the Raw\_WB\_Sets store where Raw\_WB\_Data.Contact\_Id is equal to RDC\_Delete\_Drct.Contact\_Id.   
Output RDC\_Delete\_Stat to the MACS with message indicating the success or failure of the delete.

## Reusability

This function will be performed by the UNIX operating system.

## 4.4.2 Performance Requirements

The following list summarizes the performance requirements allocated to the RDCS:

4.4.2.1 The RDCS software on each LPS string shall generate the information necessary to produce a data receive summary for received wideband data within 10 seconds of the conclusion of its capture.

4.4.2.2 The RDCS software on each LPS string shall produce a data receive summary for the most recently received wideband data within 10 seconds of the receipt of an appropriate directive from the MACS.

4.4.2.3 The RDCS software on each LPS string shall provide the capability to receive the equivalent of any combination of the format 1 and format 2 portions of 125 Landsat 7 ETM+ scenes of wideband data per day (approximately 25-30 GB per day).

4.4.2.4 The RDCS software on each LPS string shall provide the capability to copy received wideband data to removable media at a minimum rate of 7.5 Mbps.

4.4.2.5 The RDCS software on each LPS string shall provide the capability to copy received wideband data to removable media concurrently with Level 0R processing of that data.

4.4.2.6 The RDCS software on each LPS string shall provide the capability to reprocess a maximum of 10% of a string's daily input volume of wideband data (approximately 12.5 scenes or 2.5-3 GB per day).

4.4.2.7 The RDCS software on each LPS string shall provide the capability to copy received wideband data to removable media at a daily average aggregate rate of not less than 3 megabits per second (Mbps) (Includes 10% of overhead due to reprocessing).

4.4.2.8 The RDCS software on each LPS string shall maintain data processing throughput performance for all Landsat 7 raw wideband data received with a BER of one bit error in 105 bits, without loss of Level OR processed data and without retransmission.

4.4.2.9 The RDCS software on each LPS string shall provide the capability of receiving wideband data from a single LGS output channel at a maximum rate of 75 Mbps.

4.4.2.10 The RDCS software on each LPS string shall provide the capability to receive wideband data for Landsat 7 contact periods of up to 14 minutes.

4.4.2.11 The RDCS software on each LPS string shall output any periodic processing status information that it generates with a maximum latency of 30 seconds between outputs.

## 4.5 Raw Data Processing Subsystem (RDPS)

This subsystem is responsible for processing the raw wideband data on a contact period basis, including synchronization of the frames, performing various error detection and correction techniques on the data and, upon request, generating a report on the quality of the data.

## 4.5.1 Functional Requirements

The following list summarizes the functional requirements allocated to the RDPS:

• validate and store the processing parameters received from MACS.

• process the wideband data on a contact period basis.

• detect and synchronize on normal and inverted polarity wideband data concurrently

• the synchronization shall utilize a Search/Check/Lock/ Flywheel(SCLF) strategy.

• invert bits with inverted polarity.

• correct bit slips.

• perform PN decoding.

• perform CCSDS AOS Grade 3 service.

• store all CADUs which have failed the CCSDS AOS Grade 3 checks.

• delete VCDUs containing fill data.

• perform BCH error detection and correction.

• store all CADUs which have failed BCH error detection and correction on the mission data zone.

• generate a return link quality and accounting report on a Landsat 7 contact period basis.

• annotate the CADU with the VCID information.

• compute the Bit Error Rate (BER).

## 4.5.1.1 Major Functions

The Raw Data Processing Subsystem first checks the CCSDS parameters for valid values and stores these parameters if they are valid. If the CCSDS parameters are invalid default values will be used.

The raw wideband data is retrieved for the contact period requested by the operator. The frames are then synchronized using the search, check, lock, flywheel strategy. Following SCLF synchronization, the frames are aligned on byte boundaries and, if the frame sync pattern is inverted, the data is normalized reversing the data inversion. The data is then decoded to reverse the Pseudo-Random Noise encoding.

Grade 3 error detection is performed including a Cyclic Redundancy Checksum calculation and Reed-Solomon checks on the header. Any fill CADUs are discarded.

The final error detection performed on the data is the BCH Decode process that is performed on the mission and pointer data fields. This process also attempts to correct the data. Copies of the CADUs that fail the error detection processes are saved. The VCDUs are annotated to reflect the data quality, and any change in the VCID. They are also annotated to mark the end of the contact period. The bit error rate is calculated and information pertaining to the quality of the data is stored to be used in the generation of the return link quality and accounting report.

The major functions of the RDPS are depicted in the following data flow diagrams.

## 4.5.1.2 Interface Requirements

The following two tables summarize the interface requirements for the RDPS:

Table 4.3 RDPS Interface Requirements - INPUT
<table><tr><td rowspan=1 colspan=1>Input Item Name</td><td rowspan=1 colspan=1>Source</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>RDP_CCSDS_Parms</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>CCSDS Parameters</td></tr><tr><td rowspan=1 colspan=1>RDP_Thresholds</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Error Thresholds</td></tr><tr><td rowspan=1 colspan=1>Raw_WB_Sets</td><td rowspan=1 colspan=1>RDCS</td><td rowspan=1 colspan=1>Raw Wideband Data Store</td></tr><tr><td rowspan=1 colspan=1>RDP_Process_Drct</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Directive containing the contactperiod for which to process theraw wideband data</td></tr><tr><td rowspan=1 colspan=1>RDP_Rpt_Return_Link_QA_Drct</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Directive containing the contactperiod for which to generate areturn link qualityandaccounting report</td></tr></table>

Table 4.4 RDPS Interface Requirements - OUTPUT
<table><tr><td rowspan=1 colspan=1>Output Item Name</td><td rowspan=1 colspan=1>Destination</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>Ann_VCDU</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>VCDU annotated with contact id,data quality indicator, VCIDchange flag, and end of dataindicator</td></tr><tr><td rowspan=1 colspan=1>Report_RDP_Return_Link_QA</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>ReturnLinkQualityandAccounting Report</td></tr><tr><td rowspan=1 colspan=1>RDP_Acct</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Metadata Accounting Information</td></tr><tr><td rowspan=1 colspan=1>RDP_Setup_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Status of errors in the CCSDSparameters         and/or        RDPthresholds</td></tr><tr><td rowspan=1 colspan=1>RDP_Sync_Err_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Notification that synchronizationerrors have exceeded the errorthresholds</td></tr><tr><td rowspan=1 colspan=1>RDP_RS_Err_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Notification that errors duringReed-Solomon processing haveexceeded the error thresholds</td></tr><tr><td rowspan=1 colspan=1>RDP_CRC_Err_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Notification that errors duringCyclic      Redundancy      Checkprocessing have exceeded theerror thresholds</td></tr><tr><td rowspan=1 colspan=1>RDP_BCH_Err_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Notification that errors duringBCH decode processing haveexceeded the error thresholds</td></tr><tr><td rowspan=1 colspan=1>RDP_BER_Err_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Notification that the bit error ratehas exceeded the BER threshold</td></tr></table>

## 4.5.1.3 Detailed Functional Requirements

This section contains the process specifications for the lowest level processes in the RDPS data flow diagrams.

NAME: 2.1;9

TITLE: Validate RDP Parameters

INPUT/OUTPUT: RDP\_Thresholds : data\_out RDP\_Setup\_Status : data\_out RDP\_CCSDS\_Parms : data\_out RDP\_CCSDS\_Parms : data\_in RDP\_Thresholds : data\_in

## BODY:

Description of Process Validate the CCSDS Parameters and RDP Thresholds received from the MACS and store the valid values.

## Assumptions

Preconditions None.

Postconditions MACS is notified if there are invalid CCSDS parameters or RDP thresholds.

## Constraints

The parameters must conform to predefined thresholds The processing of data for a contact period will not be interrupted to process updates to the CCSDS parameters.

## Functional Breakdown

alidate that the RDP\_CCSDS\_Parms are within the following ranges: RDP\_CCSDS\_Parms.CADU\_Search\_Tolerance: 1 to 3 RDP\_CCSDS\_Parms.CADU\_Check\_Tolerance: 0 to 3 RDP\_CCSDS\_Parms.CADU\_Lock\_Tolerance: 0 to 3 RDP\_CCSDS\_Parms.CADU\_Flywheel\_Tolerance: 0 to 3 RDP\_CCSDS\_Parms.CADU\_Sync\_Marker\_Check\_Error\_Tolerance: 0 to 3 RDP\_CCSDS\_Parms.CADU\_Sync\_Lock\_Error\_Tolerance: 0 to 3 RDP\_CCSDS\_Parms.CADU\_Bit\_Slip\_Correction\_Extent: 0 to 3 Store the valid CCSDS parameters in Valid\_CCSDS\_Parms.

Check that the RDP Threshold parameters (RDP\_Thresholds) are non-negative integers.

Store only the valid RDP thresholds in the Valid\_RDP\_Thres data store.

Send a message to the MACS specifying the names and values of any CCSDS parameters or RDP\_Thresholds parameters that are in error in RDP\_Status.RDP\_Setup\_Status.

Reusability None.

NAME: 2.2.1

TITLE: Perform SCLF Sync

INPUT/OUTPUT: Chan\_Acss\_Acct : data\_inout Contact\_Id : data\_out RDP\_Sync\_Err\_Status : data\_out Sync\_WB\_Data : data\_out Valid\_CCSDS\_Parms : data\_in Raw\_Data\_Byte\_Stream : data\_in RDP\_Process\_Drct : data\_in Sync\_Thres : data\_in

## BODY:

Description of Process This process uses the Search, Check, Lock, Flywheel strategy to locate frame sync patterns in the Raw\_Data\_Byte\_Stream.

## Assumptions

Preconditions Valid\_CCSDS\_Parms and the RDP\_Process\_Drct have been received.

## Postconditions

Sync\_WB\_Data which contains the Contact\_Id, Raw\_Data\_Byte\_Stream, frame sync marker locations, and Sync\_Annotation have been sent to Align Bytes.   
MACS has been notified if the cumulative number of frame sync errors have exceeded the tolerance stored in Valid\_RDP\_Thres.Sync\_Thres   
The RDP\_Acct contains NULL fields for the specified Contact\_Id for all return link QA information not provided by this process

Constraints The expected frame sync pattern (1acffc1d) must exist in the data stream and must be spaced a CADU length apart, within bit slip or flywheel tolerance range.

## Functional Breakdown

Retrieve the Raw\_Data\_Byte\_Stream associated with the Contact\_Id specified in the RDP\_Process\_Drct from the Raw\_WB\_Sets   
Place the Contact\_Id into the Sync\_WB\_Data.Contact\_Id.   
Retrieve the Valid\_CCSDS\_Parms.   
Utilize the search/check/lock/flywheel strategy to locate the valid normal and inverted frame synchronization markers Sync\_WB\_Data. Polarity\_Unknown\_Sync.Sync and Sync\_WB\_Data.Polarity\_Unknown\_Sync. Inverted\_Sync.   
Detect Sync\_WB\_Data.Polarity\_Unknown\_Sync.Sync and Sync\_WB\_Data. Polarity\_Unknown\_Sync.Inverted\_Sync with +- 3 bit slips, and fill or truncate the frame length accordingly   
After each valid synchronization pattern is located, provide the

synchronization marker exact location in Sync\_WB\_Data.Sync\_Loc along with the Sync\_WB\_Data.Sync\_Annotation.

Set the Ann\_VCDU.End\_Of\_Contact\_Flag (set to TRUE for the final BCH\_Chkd\_VCDU for the contact period) to indicate the end of the contact period.

During all modes allow the error tolerance indicated in

Valid\_CCSDS\_Parms.CADU\_Sync\_Lock\_Error\_Tolerance,

Valid\_CCSDS\_Parms.CADU\_Sync\_Marker\_Check\_Error\_Tolerance., Valid\_CCSDS\_Parms.CADU\_Bit\_Slip\_Correction\_Extent

During all modes accumulate

Chan\_Acss\_Acct.CADU\_Polarity, Chan\_Acss\_Acct.CADU\_Bit\_Slip,

Chan\_Acss\_Acct.CADU\_Sync\_Error\_Count,

Chan\_Acss\_Acct.CADU\_Rcv\_Count,

Chan\_Acss\_Acct.CADU\_Flywheel\_Count, and

Chan\_Acss\_Acct.CADU\_Missing\_Count

Insert the Valid\_CCSDS\_Parms into the Chan\_Acss\_Acct.Valid\_CCSDS\_Parms.

Place the RDP\_Process\_Drct.Contact\_Id into Chan\_Acss\_Acct.Contact\_Id.

Place the Chan\_Acss\_Acct into the RDP\_Acct store identified by the Chan\_Acss\_Acct.Contact\_Id.

For every cumulative error detected, compare with the threshold value stored in Valid\_RDP\_Thres.Sync\_Thres.

If the number of cumulative errors per contact period exceeds the threshold, then

Send a RDP\_Status.RDP\_Sync\_Err\_Status to the MACS indicating the tolerance has been exceeded.

Output the RDP\_Process\_Drct.Contact\_Id

Output the Sync\_WB\_Data.

## Reusability

A frame sync lookup table would allow bit flips in addition to bit slips. A prototype exists for portions of this process which will be examined for reuse.

NAME: 2.2.2;3

TITLE: Align Bytes

INPUT/OUTPUT: Aln\_CADU : data\_out Aln\_Inver\_CADU : data\_out Sync\_WB\_Data : data\_in

## BODY:

Description of Process This process takes each frame of data starting with the first frame sync pattern detected and aligns the entire frame on a byte boundary.

## Assumptions

The location of the frame sync patterns is known. The frame size is known. The raw wideband data has been extracted on a contact period basis.

Postconditions Every CADU frame has been aligned on a byte boundary. Fill data is used if the frame size is not an even multiple of the increment being shifted.

Constraints None

## Functional Breakdown

Obtain the location of the frame sync pattern from the Sync\_WB\_Data. Calculate the distance needed to shift the data.   
Shift the entire frame to align on a byte boundary   
Complete the Aln\_CADU by adding fill data to the remainder of the frame.   
If the frame sync pattern is inverted, then Place Sync\_WB\_Data.Contact\_Id into Aln\_Inver\_CADU.Contact\_Id. Output the Aln\_Inver\_CADU,   
Otherwise Place Sync\_WB\_Data.Contact\_Id into Aln\_CADU.Contact\_Id. Output Aln\_CADU.

## Reusability

A prototype exists for this process which will be examined for reuse.

NAME: 2.2.3;3

TITLE: Deinvert Data

INPUT/OUTPUT: Aln\_CADU : data\_out Aln\_Inver\_CADU : data\_in

## BODY: BODY:

Description of Process This process flips the bits of an entire CADU.

## Assumptions

Preconditions The frame sync pattern for the CADU is inverted.

Postconditions The entire CADU is deinverted (normalized).

Constraints None.

Functional Breakdown Flip all bits of the Aln\_Inver\_CADU(0->1, 1->0) to create the bits of the Aln\_CADU. Place the Aln\_Inver\_CADU.Contact\_Id into Aln\_CADU.Contact\_Id.

Reusability A prototype exists for this process and it will be examined for reuse.

NAME: 2.2.4;5

TITLE: Perform PN Decode

INPUT/OUTPUT: Ann\_CADU : data\_out Aln\_CADU : data\_in

BODY:   
Description of Process This process decodes the data to reverse the PN encoding on the data

## Assumptions

Preconditions CADUs have been byte aligned in the Align Bytes procoss. Inverted data has been normalized in the Deinvert Data process.

Postconditions Data is PN decoded

Constraints None.

## Functional Breakdown

The Aln\_CADU is PN decoded using a standard pseudo-random sequence generated by a polynomial described in CCSDS 101.0-B-3, paragraphs 6.3, 6.4, and 6.5 to transform the Aln\_CADU to an Ann\_CADU.   
Place the Aln\_CADU.Contact\_Id into Ann\_CADU.Contact\_Id.   
Output the Ann\_CADU.

## Reusability

A prototype exists for this function which will be considered for reuse.

NAME: 2.3.1;11

TITLE: Perform CRC Check

INPUT/OUTPUT: CRC\_Acct : data\_inout RDP\_CRC\_Err\_Status : data\_out CRC\_Failed\_CADU : data\_out CRC\_Chkd\_CADU : data\_out Ann\_CADU : data\_in CRC\_Thres : data\_in

## BODY:

Description of Process This process performs a 16 bit Cyclic Redundancy Checksum on the CADU

## Assumptions

Preconditions The data has been synchronized, byte aligned, CRC encoded, and PN decoded.

Postconditions CRC errors are reported to the CRC\_Acct.

Constraints None

## Functional Breakdown

Perform a Cyclic Redundancy Checksum on the Ann\_CADU data using the generator polynomial and procedure described in the CCSDS 701.0-B-1 section 5.4.9.2.1.4.2.c   
Place the Ann\_CADU.Contact\_Id into the CRC\_Acct.Contact\_Id.   
Update the RDP\_Acct store identified by the CRC\_Acct.Contact\_Id with the accumulated CRC\_Acct information.   
If the CADU fails the CRC check, then Place the CRC\_Failed\_CADU into the Faild\_CADUs store identified by Ann\_CADU.Contact\_Id.   
For every CRC error detected, Fetch the threshold value stored in Valid\_RDP\_Thres.CRC\_Thres. If the cumulative number of CRC errors per contact period threshold value is exceeded, then Send a RDP\_Status.RDP\_CRC\_Err\_Status message to the MACS indicating that the Valid\_RDP\_Thres.CRC\_Thres tolerance has been exceeded   
Output the CRC\_Chkd\_CADUs.

## Reusability

A prototype of this process is being developed and will be examined for reuse.

NAME: 2.3.2;13

TITLE: Perform RS\_EDAC Check

INPUT/OUTPUT:   
RS\_Acct : data\_inout   
RDP\_RS\_Err\_Status : data\_out   
RS\_Failed\_CADU : data\_out   
RS\_Corr\_CADU : data\_out   
CRC\_Chkd\_CADU : data\_in   
RS\_Thres : data\_in

## BODY:

Description of Process This process performs Reed Solomon error detection and correction on the VCDU header.

## Assumptions

Preconditions Data has been synchronized, byte aligned, PN decoded and RS encoded

Postconditions If errors are detected and the error tolerance for Reed Solomon has not been exceeded, the VCDU header is considered corrected.

Constraints None

## Functional Breakdown

Receive CRC\_Chkd\_CADU and use bits 48 through 63 (16 bits) of the VCDU header as the check symbols of the shortened Reed-Solomon (10,6) code.   
If the VCDU\_Hdr\_Bytes contained within CRC\_Chkd\_CADU.VCDU\_Bytes are uncorrectable, then Place the RS\_Failed\_CADU into the Faild\_CADUs store identified by the CRC\_Chkd\_CADU.Contact\_Id. Accumulate the RS\_Acct.VCDU\_Header\_Uncorrectable\_Count.   
Otherwise, Place CRC\_Chkd\_CADU.Contact\_Id into the RS\_Corr\_CADU.Contact\_Id. If this is a fill VCDU, then Place the VCDU\_Fill\_Hdr\_Bytes in the RS\_Corr\_CADU Otherwise Place the VCDU\_Hdr\_Bytes in the RS\_Corr\_CADU. The remaining data portion of the VCDU will be identified as the RS\_Corr\_CADU.VCDU\_Data. Place the RS\_Annotation into the RS\_Corr\_CADU.RS\_Annotation.   
If the RS\_Corr\_CADU has a VCID corresponding to format 1, then Accumulate the RS\_Acct.VCDU\_Header\_Correctable\_Count. VCDU\_Hdr\_Fmt1\_Correctable\_Err\_Cnt   
If the RS\_Corr\_CADU has a VCID corresponding to format 2, then Accumulate the RS\_Acct.VCDU\_Header\_Correctable\_Count. VCDU\_Hdr\_Fmt2\_Correctable\_Err\_Cnt

Place the RS\_Corr\_CADU.Contact\_Id into RS\_Acct.Contact\_Id.

Update the RDP\_Acct store identified by the RS\_Acct.Contact\_Id with the accumulated RS\_Acct information.

For every uncorrectable header detected, fetch the threshold value stored in Valid\_RDP\_Thres.RS\_Thres.

If the cumulative number of RS errors per contact period threshold value is exceeded, then

Send a RDP\_Status.RDP\_RS\_Err\_Status message to the MACS

stating that the Valid\_RDP\_Thres.RS\_Thres has been exceeded. Output the RS\_Corr\_CADU.

Reusability

None.

NAME: 2.3.3;3

TITLE: Discard Fill CADUs

INPUT/OUTPUT: Grade\_3\_Chkd\_VCDU : data\_out RS\_Corr\_CADU : data\_in

BODY:   
Description of Process This process discards all CADUs with fill data.

## Assumptions

Preconditions Data has been synchronized, byte aligned, and RS checked

Postconditions Fill CADUs have been discarded

Constraints None.

Functional Breakdown Check the RS\_Corr\_CADU.VCDU\_Fill\_Hdr\_Bytes for the reserved value of "all ones" If the RS\_Corr\_CADU.VCDU\_Fill\_Hdr\_Bytes value is all ones, discard the CADU Otherwise, Output the Grade\_3\_Chkd\_VCDU.

Reusability None.

NAME:   
2.4;11   
TITLE:   
Decode BCH

INPUT/OUTPUT: BCH\_Acct : data\_inout RDP\_BCH\_Err\_Status : data\_out BCH\_Chkd\_VCDU : data\_out BCH\_Failed\_VCDU : data\_out Grade\_3\_Chkd\_VCDU : data\_in BCH\_Thres : data\_in

## BODY:

Description of Process This process checks the codewords of the VCDU mission and pointer data for bit errors and attempts to correct the errors.

## Assumptions

Preconditions This process will only be executed if there are any bit slips, frame sync errors, Reed-Solomon errors, or CRC errors in the Grade\_3\_Chkd\_VCDU.

Postconditions The VCDU has been further annotated with the mission and pointer field check quality indicators. A copy of the VCDUs which failed the BCH EDAC on the mission data zone has been saved.

Constraints None

Functional Breakdown Decode the mission data zone and data pointer of the Grade\_3\_Chkd\_VCDU which have been encoded by the polynomials defined in the Landsat 7 System Data Format Control Book, sections 3.1.2.1.2 and 3.1.2.1.3. Attempt to correct the bit errors. Place the Grade\_3\_Chkd\_VCDU.Contact\_Id into the BCH\_Chkd\_VCDU.Contact\_Id. Place the Grade\_3\_Chkd\_VCDU data into the BCH\_Chkd\_VCDU If the bits are BCH corrected, then Insert the corrected bits into the BCH\_Chkd\_VCDU. BCH\_Corrected\_Data Accumulate the BCH\_Acct.BCH\_Data\_Corrected\_Error\_Count, BCH\_Acct.BCH\_Pointer\_Corrected\_Error\_Count, BCH\_Acct.BCH\_Data\_Uncorrected\_Error\_Count, BCH\_Acct.BCH\_Pointer\_Uncorrected\_Error\_Count, and BCH\_Acct.BCH\_Bits\_Corrected If the error counts exceed the Valid\_RDP\_Thres.BCH\_Thres, then Send the RDP\_Status.RDP\_BCH\_Err\_Status containing the number of BCH errors to the MACS.

If the VCDU is uncorrectable for the mission data zone, then

Output the BCH\_Failed\_VCDU to the Failed\_CADUs store identified by the Grade\_3\_Chkd\_VCDU.Contact\_Id.

Place the BCH\_Chkd\_VCDU.Contact\_Id into BCH\_Acct.Contact\_Id.

Update the RDP\_Acct store identified by the BCH\_Acct.Contact\_Id with

the accumulated BCH\_Acct information.

Place the Data\_Field\_Qual\_Indicator into the BCH\_Annotation.

Data\_Field\_Qual\_Indicator to indicate that the data is

"CORRECTABLE", "UNCORRECTABLE", or has "NO\_ERRORS".

Place the BCH\_Bits\_Corrected into the BCH\_Annotation.

Append the BCH\_Annotation to the BCH\_Chkd\_VCDU.

Output the BCH\_Chkd\_VCDU.

## Reusability

See the Landsat 7 Mission Data and Data Pointer BCH Decoder Prototype

Description for possible reuse of the prototype.

NAME: 2.5;7

TITLE: Annotate VCID Change

INPUT/OUTPUT: Curr\_VCID : data\_out Ann\_VCDU : data\_out BCH\_Chkd\_VCDU : data\_in Prev\_VCID : data\_in Contact\_Id : data\_in

## BODY:

Description of Process This process determines if there is a change in the virtual channel of the VCDU and annotates the Ann\_VCDU to indicate the change.

## Assumptions

Preconditions Frame sync, CRC and Reed-Solomon checks have been performed on the VCDUs. Fill CADUs have been discarded. The previous VCID has been retained.

Postconditions The VCDU has been annotated with a VCID change flag.

Constraints None.

Place the BCH\_Chkd\_VCDU.Contact\_Id into the Ann\_VCDU.Contact\_Id.   
Place the BCH\_Chkd\_VCDU information into the Ann\_VCDU.   
If the Saved\_VCID.Prev\_VCID differs from the Curr\_VCID, then Set the Ann\_VCDU.VCID\_Change\_Flag to TRUE to indicate a change in the VCID.   
Otherwise, Set the Ann\_VCDU.VCID\_Change\_Flag to FALSE to indicate no change in the VCID.   
Output the Curr\_VCID to the Saved\_VCID data store.   
Output the Ann\_VCDU.

Reusability None.

NAME: 2.6;8

TITLE: Compute BER

INPUT/OUTPUT:   
RDP\_BER\_Err\_Status : data\_out   
BER\_Acct : data\_out   
BER\_Thres : data\_in   
RDP\_Acct : data\_in   
Contact\_Id : data\_in

## BODY:

Description of Process This process computes the Bit Error Rate of the VCDU.

## Assumptions

Preconditions None.

Postconditions None.

Constraints None.

Functional Breakdown Use Contact\_Id to identify the associated contact period in the RDP\_Acct store. Compute the BER by dividing the sum of RDP\_Acct.BCH\_Data\_Corrected\_Error\_Count + RDP\_Acct.BCH\_Data\_Uncorrected\_Error\_Count + RDP\_Acct.BCH\_Pointer\_Corrected\_Error\_Count + RDP\_Acct.BCH\_Pointer\_Uncorrected\_Error\_Count + RDP\_Acct.CRC\_Acct.CADU\_CRC\_Error\_Count by the RDP\_Acct.CADU\_Rcv\_Count multiplied by the bits per CADU If the BER exceeds the Valid\_RDP\_Thres.BER\_Thres value, then Send an RDP\_Status.RDP\_BER\_Err\_Status message to the MACS specifying the calculated BER. Place the Contact\_Id into the BER\_Acct.Contact\_Id. Place the BER into the BER\_Acct.BER. Accumulate the BER\_Acct in the RDP\_Acct identified by BER\_Acct.Contact\_Id.

## Reusability

None.

NAME: 2.7;10

TITLE: Generate Return Link QA Report

INPUT/OUTPUT:   
Report\_RDP\_Return\_Link\_QA : data\_out RDP\_Acct : data\_in   
RDP\_Rpt\_Return\_Link\_QA\_Drct : data\_in   
BODY:   
Description of Process This process generates a report of the raw wideband data quality and accounting information on a contact period basis

## Assumptions mptions

Preconditions All of the required quality and accounting information will be available in the RDP account   
Postconditions None   
Constraints None

Functional Breakdown Set Report\_RDP\_Return\_Link\_QA.Contact\_Id to RDP\_Rpt\_Return\_Link\_QA\_Drct. Contact\_Id. Using RDP\_Rpt\_Return\_Link\_QA\_Drct.Contact\_Id, extract the following information from RDP\_Acct and place it into Report\_RDP\_Return\_Link\_QA:

RDP\_Acct.CADU\_Polarity   
RDP\_Acct.CADU\_Bit\_Slip   
RDP\_Acct.CADU\_Sync\_Error\_Count   
RDP\_Acct.CADU\_Rcv\_Count   
RDP\_Acct.CADU\_Flywheel\_Count   
RDP\_Acct.CADU\_Missing\_Count   
RDP\_Acct.VCDU\_Header\_Correctable\_Error\_Count. VCDU\_Hdr\_Fmt1\_Correctable\_Err\_Cnt   
RDP\_Acct.VCDU\_Header\_Correctable\_Error\_Count. VCDU\_Hdr\_Fmt2\_Correctable\_Err\_Cnt   
RDP\_Acct.VCDU\_Header\_Uncorrectable\_Error\_Count RDP\_Acct.BCH\_Data\_Corrected\_Error\_Count   
RDP\_Acct.BCH\_Pointer\_Corrected\_Error\_Count   
RDP\_Acct.BCH\_Data\_Uncorrected\_Error\_Count   
RDP\_Acct.BCH\_Pointer\_Uncorrected\_Error\_Count RDP\_Acct.CADU\_CRC\_Error\_Count   
RDP\_Acct.BER

Compute Report\_RDP\_Return\_Link\_QA.Approx\_Data\_Received (the approximate amount of data received in megabytes) by multiplying the RDP\_Acct.CADU\_Rcv\_Count by the number of megabytes per CADU (.001040).

Compute Report\_RDP\_Return\_Link\_QA.Approx\_Major\_Frame\_Count (the approximate count of major frames) by dividing the RDP\_Acct.CADU\_Rcv\_Count by the approximate CADUs per major frame(742).

Compute Report\_RDP\_Return\_Link\_QA.Approx\_ETM\_Count (the approximate number of ETM+ scenes) by dividing the approximate count of major frames by the approximate frames per scene

Reusability

This function will mostly use COTS software, ORACLE.

## 4.5.2 Performance Requirements

The Raw Data Processing Subsystem has the following performance requirements:

4.5.2.1 The RDPS software on each LPS string shall provide the capability to process the equivalent of any combination of the format 1 and format 2 portions of 125 Landsat 7 ETM+ scenes of wideband data per day (approximately 25-30 GB per day).

4.5.2.2 The RDPS software on each LPS string shall process received wideband data at a minimum rate of not less than 7.5 Mbps. (based on a peak raw wideband throughput of 7.5 Mbps).

4.5.2.3 The RDPS software on each LPS string shall provide the capability to execute concurrently with all other LPS subsystems.

4.5.2.3.1 The RDPS software shall begin to process received raw wideband data immediately upon receipt of required inputs.

4.5.2.3.2 The RDPS software shall output the equivalent of one Landsat 7 ETM+ scene (215,445 CADUs) within 250 seconds of the time either at the beginning of processing or the time of its last output.

4.5.2.4 The RDPS software on each LPS string shall provide the capability to reprocess a maximum of 10% of a string's daily input volume of wideband data (approximately 12.5 scenes or 2.5-3 GB per day).

4.5.2.5 The RDPS software on each LPS string shall provide the capability to process received wideband data at a daily average aggregate rate of 3 megabits per second (Mbps) (Includes 10% of overhead due to reprocessing).

4.5.2.6 The RDPS software on each LPS string shall maintain data processing throughput performance for all Landsat 7 raw wideband data received with a BER of one bit error in 105 bits, without loss of level zero processed data and without retransmission.

4.5.2.7 The RDPS software on each LPS string shall provide the capability to retrieve retained wideband data at rates equal to or greater than 7.5 Mbps.

4.5.2.8 The RDPS software on each LPS string shall output any periodic processing status information that it generates with a maximum latency of 30 seconds between outputs.

## 4.6 Major Frame Processing Subsystem (MFPS)

This subsystem is responsible for identifying a major frame and determining the major frame time. This subsystem determines the subinterval from the major frame time, the VCID, or the contact period. The MFPS generates calibration and MSCD Level 0R files on a subinterval basis and scene data on a major frame basis. The MFPS generates all Level 0R quality and accounting information.

## 4.6.1 Functional Requirements

The following list summarizes the functional requirements allocated to the MFPS:

• validate and store the processing parameters received from MACS

• identify and collect VCDUs on a major frame basis.

• locate the minor frames that contain synchronization, major frame time, end of line code, scene data, calibration data, and MSCD.

extract PCD/Status data and identify the number of missing VCDUs.

• determine the major frame time.

• determine the subinterval.

• deinterleave and align wideband data on a major frame basis.

• extract, process, and generate calibration and MSCD files on a subinterval basis.

• collect and generate Level 0R quality and accounting information on a subinterval basis.

## 4.6.1.1 Major Functions

The following is a summary of the major functions:

Setup parameters and threshold values are validated upon receipt from the MACS.

In Identify VCDUs, VCDUs are collected for one major frame according to the scan bit and the VCID. Error checking is performed on the VCDU sequence counter. Missing VCDUs are identified during this time. The VCID change and end of contact information are extracted here.

The Extract PCD process receives one VCDU at a time, plus the number of missing VCDUs, and an end of contact flag. The PCD bytes are extracted from the VCDU and sent to PCDS, along with the number of missing VCDUs, and the end of contact flag.

Parse Major Frame is responsible for locating, extracting and validating the major frame synchronization, the end of line codes, and the major frame time. Level 0R quality and accounting information is aggregated until a subinterval is detected. When a subinterval is detected, the Level 0R quality and accounting information is placed into the accounting store and the Level 0R quality and accounting aggregation store is reinitialized.

During Generate Band Data, the wide band data is deinterleaved and reversed. Band alignment takes place according to the sensor alignment information. In the case of missing major frames, MFPS outputs aligned bands containing fill.

The Extract Calibration and MSCD process handles extraction of data and the generation of the calibration and MSCD Level 0R files.

Quality and accounting from the Extract Calibration and MSCD process and Parse Major Frame process is collected on a subinterval basis and stored together. Level 0R quality and accounting reports for a given subinterval are generated on request.

The major functions of MFPS are depicted in the following data flow diagrams.

## 4.6.1.2 Interface Requirements

The following two tables summarize the interface requirements for the MFPS:

Table 4.5 MFPS Interface Requirements - INPUT
<table><tr><td rowspan=1 colspan=1>Input Item Name</td><td rowspan=1 colspan=1>Source</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>Current_Time</td><td rowspan=1 colspan=1>TimeSource</td><td rowspan=1 colspan=1>System wide time source</td></tr><tr><td rowspan=1 colspan=1>Ann_VCDU</td><td rowspan=1 colspan=1>RDPS</td><td rowspan=1 colspan=1>Annotated VCDUs</td></tr><tr><td rowspan=1 colspan=1>MFP_Rpt_LOR_QA_Drct</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Request for a report</td></tr><tr><td rowspan=1 colspan=1>MFP_Parms</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Setup parameters for the MFPS</td></tr><tr><td rowspan=1 colspan=1>MFP_Thresholds</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Setup thresholds for the MFPS</td></tr></table>

Table 4.6 MFPS Interface Requirements - OUTPUT
<table><tr><td rowspan=1 colspan=1>Output Item Name</td><td rowspan=1 colspan=1>Destination</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>PCD_Info</td><td rowspan=1 colspan=1>PCDS</td><td rowspan=1 colspan=1>PCD and related VCDUinformation</td></tr><tr><td rowspan=1 colspan=1>Major_Frame_Time</td><td rowspan=1 colspan=1>PCDS</td><td rowspan=1 colspan=1>Major frame time</td></tr><tr><td rowspan=1 colspan=1>Aligned_Bands</td><td rowspan=1 colspan=1>IDPS</td><td rowspan=1 colspan=1>Bands aligned along band anddetector</td></tr><tr><td rowspan=1 colspan=1>Status_Info</td><td rowspan=1 colspan=1>IDPS</td><td rowspan=1 colspan=1>Status information from the VCDU</td></tr><tr><td rowspan=1 colspan=1>Report_MFP_LOR_QA</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Level OR quality and accountinginformation for a subinterval</td></tr><tr><td rowspan=1 colspan=1>MFP_Setup_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Return status for the MFP_Setupparameters</td></tr><tr><td rowspan=1 colspan=1>MFP_Cal_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Return status for messages</td></tr><tr><td rowspan=1 colspan=1>MFP_MSCD_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Return status for messages</td></tr><tr><td rowspan=1 colspan=1>MFP_Mjf_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Return status for messages</td></tr><tr><td rowspan=1 colspan=1>Sub_Intv</td><td rowspan=1 colspan=1>PCDS, IDPS,MACS</td><td rowspan=1 colspan=1>Subinterval id, start time andstop time</td></tr><tr><td rowspan=1 colspan=1>MFP_Acct</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Metadata accounting information</td></tr><tr><td rowspan=1 colspan=1>Cal_File</td><td rowspan=1 colspan=1>LDTS</td><td rowspan=1 colspan=1>Calibration file</td></tr><tr><td rowspan=1 colspan=1>MSCD_File</td><td rowspan=1 colspan=1>LDTS</td><td rowspan=1 colspan=1>Mirror scan correction data file</td></tr></table>

## 4.6.1.3 Detailed Functional Requirements

This section contains the process specifications for the lowest level processes in the MFPS data flow diagrams.

NAME: 3.1;10

TITLE: Validate MFP Parameters

INPUT/OUTPUT: MFP\_Parms : data\_out MFP\_Setup\_Status : data\_out MFP\_Thresholds : data\_out MFP\_Parms : data\_in MFP\_Thresholds : data\_in Max\_Alignment\_Value : data\_in

## BODY:

Description of Process Receive and validate all MFP\_Thresholds and MFP\_Parms parameters from the MACS.

Assumptions Preconditions None.

Postconditions MFP\_Setup\_Status is output to the MACS. All threshold values are placed into the data store Valid\_MFP\_Thres. All remaining parameters are placed into the data store Valid\_MFP\_Parms.

Constraints None.

## Functional Breakdown

If MFP\_Parms.Max\_Alignment\_Value exists and MFP\_Parms.Max\_Alignment\_Value is greater than 0 and MFP\_Parms.Sensor\_Alignment\_Info exists and some element of MFP\_Parms.Sensor\_Alignment\_Info is greater than MFP\_Parms.Max\_Alignment\_Value, then Add a sensor alignment info error message to MFP\_Setup\_Status.   
If MFP\_Parms.Max\_Alignment\_Value does not exist or MFP\_Parms. Max\_Alignment\_Value is less than or equal to 0 and MFP\_Parms. Sensor\_Alignment\_Info exists and some element of MFP\_Parms. Sensor\_Alignment\_Info is greater than Valid\_MFP\_Parms. Max\_Alignment\_Value, then Add a sensor alignment info error message to MFP\_Setup\_Status.   
If any of the following values are part of MFP\_Parms and is less than or equal to 0 Sub\_Intv\_Delta Mjf\_Data\_Rate Time\_Range\_Tol Part\_Mnf\_Tol Maj\_Vote\_Tol

Add a sensor alignment info error message to MFP\_Setup\_Status. If MFP\_Status.MFP\_Setup\_Status contains any error messages, then

Output MFP\_Status.MFP\_Setup\_Status.

Place an acceptance message into MFP\_Status.MFP\_Setup\_Status.

Output MFP\_Status.MFP\_Setup\_Status.

Place the operator controls that appear in the first column

into the Valid\_MFP\_Parms data store.

Place the operator controls that appear in the second column into the Valid\_MFP\_Thres data store.

NAME: 3.2

TITLE: Identify VCDUs

INPUT/OUTPUT:   
Ann\_VCDU\_Collection : data\_inout   
VCDU\_With\_Fill\_Info : data\_out   
Major\_Frame\_VCDU\_Set : data\_out   
Sub\_Intv\_Info : data\_out   
Scan\_Dir\_Thr : data\_in   
Ann\_VCDU : data\_in

## BODY:

Description of Process Collect Ann\_VCDUs on a major frame basis and check the VCDU count.

## Assumptions

Preconditions Receive one Ann\_VCDU at a time. The Ann\_VCDU.VCID\_Change\_Flag is set to indicate a VCID change. The Ann\_VCDU.Sync\_Annotation.End\_Of\_Contact\_Flag indicates the last VCDU of the current contact period.

Missing VCDUs are detected and flagged in Major\_Frame\_VCDU\_Set and VCDU\_With\_Fill\_Info.   
One VCDU that contains the end of contact marker and information about the number of missing VCDUs is output to Extract PCD.   
A set of VCDUs with the same VCID, same scan bit and same contact id is sent to Parse Major Frame. The first and last VCDU of the set may not have the same attributes as the rest.

Constraints None.

## Functional Breakdown

If the previous major frame was not processed, then

Starting with the first Ann\_VCDU extract the scan bit, located in the PCD/Status field of the VCDU. This becomes the comparison variable. Place this Ann\_VCDU into the Ann\_VCDU\_Collection.

Read the scan bit, Ann\_VCDU.VCID\_Change\_Flag, and Ann\_VCDU. Sync\_Annotation.End\_Of\_Contact\_Flag from each successive Ann\_VCDU.

If the current scan bit is different from the previous scan bit, and the Ann\_VCDU.VCID\_Change\_Flag and Ann\_VCDU.Sync\_Annotation.End\_Of\_Contact\_Flag are "false", then Empty the Ann\_VCDU\_Collection store. Increment the Ann\_VCDU\_Collection.Mjf\_CADU\_Fly\_Cnt Place the Ann\_VCDU into the Ann\_VCDU\_Collection. Increment Ann\_VCDU\_Collection.Mjf\_CADU\_Fly\_Cnt.

If the current scan bit is different from the previous scan bit,

Extract the minor frame counter from VCDU\_With\_Fill\_Info.Ann\_VCDU. VCDU\_Data.

or either the Ann\_VCDU.VCID\_Change\_Flag, or   
Ann\_VCDU.Sync\_Annotation.End\_Of\_Contact\_Flag is "true", then   
Add this Ann\_VCDU as the second Ann\_VCDU to the Ann\_VCDU\_Collection store.   
Retrieve the first Ann\_VCDU from the Ann\_VCDU\_Collection.   
Place the Ann\_VCDU into VCDU\_With\_Fill\_Info.Ann\_VCDU.   
Reset VCDU\_With\_Fill\_Info.Num\_Missing\_VCDUs to zero.   
Extract the VCDU counter from VCDU\_With\_Fill\_Info.Ann\_VCDU. VCDU\_Hdr\_Bytes.   
Update the Ann\_VCDU\_Collection.Exp\_VCDU\_Ctr.   
Extract the minor frame counter from VCDU\_With\_Fill\_Info. Ann\_VCDU.VCDU\_Data   
Update the Ann\_VCDU\_Collection.Exp\_Mnf\_Ctr.   
Set VCDU\_With\_Fill\_Info.Sync\_Annotation.End\_Of\_Contact\_Flag to "false".   
Output VCDU\_With\_Fill\_Info.   
Retrieve the second Ann\_VCDU from the Ann\_VCDU\_Collection and continue behind else.

If the end of line code is expected in this VCDU, then Set Major\_Frame\_VCDU\_Set.Exp\_Eol\_Ptr to point to this Ann\_VCDU.

Read the scan bit, Ann\_VCDU.VCID\_Change\_Flag, and Ann\_VCDU. Sync\_Annotation.End\_Of\_Contact\_Flag from Ann\_VCDU.   
If the current scan bit is different from the previous scan bit, or either the Ann\_VCDU.VCID\_Change\_Flag, or Ann\_VCDU.Sync\_Annotation.End\_Of\_Contact\_Flag is "true", then verify the Ann\_VCDU\_Collection.Rel\_VCDU\_Cnt does not exceed the Valid\_MFP\_Thres.Scan\_Dir\_Thr, Set Major\_Frame\_VCDU\_Set.Mjf\_CADU\_Rcvd\_Cnt to the sum of Ann\_VCDU\_Collection.Rel\_VCDU\_Cnt and Ann\_VCDU\_Collection.Mjf\_CADU\_Fly\_Cnt. Move each Ann\_VCDU\_Collection.Ann\_VCDU, and place it into Major\_Frame\_VCDU\_Set.Ann\_VCDU.

Place Ann\_VCDU\_Collection.VCDU\_Ctr\_Err into Major\_Frame\_VCDU\_Set.VCDU\_Ctr\_Err

Place Ann\_VCDU\_Collection.Mnf\_Ctr\_Err into Major\_Frame\_VCDU\_Set.Mnf\_Ctr\_Err

Output Major\_Frame\_VCDU\_Set.

Place the Ann\_VCDU.Contact\_Id into Sub\_Intv\_Info.Contact\_Id.

Place the Ann\_VCDU.VCDU\_Hdr\_Bytes.VCID into Sub\_Intv\_Info. VCID.

If the Ann\_VCDU.VCID\_Change\_Flag is "true", then Set the Sub\_Intv\_Info.VCID\_Change\_Flag to "true".

Else Set the Sub\_Intv\_Info.VCID\_Change\_Flag to "false".

If the Ann\_VCDU.Sync\_Annotation.End\_Of\_Contact\_Flag is "true", then Set the Sub\_Intv\_Info.End\_Of\_Contact\_Flag to "true".   
Else Set the Sub\_Intv\_Info.End\_Of\_Contact\_Flag to "false".   
Output Sub\_Intv\_Info.

Else Add the Ann\_VCDU to the Ann\_VCDU\_Collection. Increment Ann\_VCDU\_Collection.Rel\_VCDU\_Cnt by 1.

Place the Ann\_VCDU into VCDU\_With\_Fill\_Info.Ann\_VCDU. Place the number of missing VCDUs into VCDU\_With\_Fill\_Info.Num\_Missing\_VCDUs. Output the VCDU\_With\_Fill\_Info.

Prototypes should be of use for the scan bit search and the check on the VCDU sequence count.

NAME: 3.3;9

TITLE: Extract PCD

INPUT/OUTPUT:   
PCD\_Info : data\_out   
VCDU\_With\_Fill\_Info : data\_in   
Sub\_Intv\_Id : data\_in   
BODY:   
Description of Process Extract PCD bytes from status field of the VCDU.

## Assumptions

Preconditions The number of missing VCDUs must be provided with VCDU\_With\_Fill\_Info

Post conditions PCD\_Info contains the four extracted PCD bytes, the number of missing VCDUs, and the end of contact marker.

Constraints None.

## Functional Breakdown Functional Breakdown

Extract words #1 through #4 of the PCD/Status data from the VCDU\_With\_Fill\_Info.Ann\_VCDU.VCDU\_Data zone and place into PCD\_Info.PCD\_Bytes.   
Place VCDU\_With\_Fill\_Info.Num\_Missing\_VCDUs into PCD\_Info.Num\_Missing\_VCDUs.   
Place VCDU\_With\_Fill\_Info.Ann\_VCDU.Sync\_Annotation. End\_Of\_Contact\_Flag into PCD\_Info.End\_Of\_Contact\_Flag.   
Place Sub\_Intv\_Id into PCD\_Info.Sub\_Intv\_Id.   
Output PCD\_Info.

Reusability None.

NAME: 3.4.1

TITLE: Identify Major Frames

INPUT/OUTPUT:   
Mjf\_QA : data\_inout   
Mjf\_VCDU\_Data : data\_out   
Failed\_Mjf\_Data : data\_out   
Time\_Code : data\_out   
Major\_Frame\_VCDU\_Set : data\_in   
Maj\_Vote\_Tol : data\_in   
Sub\_Intv\_Info : data\_in   
Part\_Mnf\_Tol : data\_in

## BODY:

Description of Process Major\_Frame\_VCDU\_Set is searched for the major frame synchronization and the end of line code.

## Assumptions

Preconditions The set of VCDUs all have the same VCID and the same scan bit, except for the first and last VCDU.

## Postconditions

Output time code minor frames.   
If the major frame synchronization is not found, the set of VCDUs are placed into Failed\_Mjf\_data. Processing of the Major\_Frame\_VCDU\_Set ends.   
If neither of the end of line codes are found, then The set of VCDUs are placed into Failed\_Mjf\_data. Processing of the Major\_Frame\_VCDU\_Set ends.   
If the synchronization and the end of line codes are found, then Output Mjf\_VCDU\_Data.   
Major frame quality and accounting information for the Major\_Frame\_VCDU\_Set (Mjf\_QA) is accumulated in the Mjf\_VCDU\_QA store

Constraints None

## Functional Breakdown

Search each minor frame in the first two Gap\_Tagged\_VCDUs.Ann\_VCDU of the Major\_Frame\_VCDU\_Set for the major frame synchronization.   
Perform a majority vote on the data word groups. The data word is accepted if it passes majority voting with a value that exceeds the Valid\_MFP\_Parms.Maj\_Vote\_Tol.   
If the synchronization is not found by the end of the second Major\_Frame\_VCDU\_Set.Gap\_Tagged\_VCDUs.Ann\_VCDU, then Check the partial minor frames. If for each of the first two Major\_Frame\_VCDU\_Set. Gap\_Tagged\_VCDUs.Ann\_VCDU, the

Major\_Frame\_VCDU\_Set.Gap\_Tagged\_VCDUs. Num\_Missing\_VCDUs is positive, then The partial minor frames of the two VCDUs will be searched for part of the major frame sync. In order for a partial minor frame to be considered, the number of data word groups must exceed Valid\_MFP\_Parms.Part\_Mnf\_Tol.

If the synchronization is not found, then If the synchronization is not found, then

The Major\_Frame\_VCDU\_Set is placed into the Failed\_Mjf\_Data store identified by Sub\_Intv\_Info.Contact\_Id.   
Increment the Mjf\_QA.Mjf\_Tossed\_Cnt.   
Processing for this major frame ends.

## Else

Search each minor frame starting in the VCDU identified in Major\_Frame\_VCDU\_Set.Exp\_Eol\_Ptr for the end of line codes.

Perform a majority vote on the data word groups. The majority vote count must exceed Valid\_MFP\_Parms.Maj\_Vote\_Tol in order to be accepted.

If neither end of line code is found, then Begin to search again starting with the first minor frame and continue until there are no more minor frames within this Major\_Frame\_VCDU\_Set.

If either end of line code is still not found, then the Major\_Frame\_VCDU\_Set is placed into the Failed\_Mjf\_Data store identified by Sub\_Intv\_Info.Contact\_Id. Increment the Mjf\_QA.Mjf\_Tossed\_Cnt. Increment the Mjf\_QA.Mjf\_Eol\_Err\_Cnt. Processing for this major frame ends.

Else

If the scan bit indicates forward, then Set Mjf\_VCDU\_Data.Direction\_Start to point to the first minor frame.

Else Set Mjf\_VCDU\_Data.Direction\_Start to point to the last minor frame.   
Output Mjf\_VCDU\_Data.

Output the Time\_Code minor frames

Place Major\_Frame\_VCDU\_Set.Mnf\_Ctr\_Err into Mjf\_QA.Mnf\_Ctr\_Err Output Mjf\_QA.

## Reusability

None.

NAME: 3.4.2;10

TITLE: Extract Major Frame Time

INPUT/OUTPUT:   
Saved\_Time : data\_inout   
Mjf\_Time\_Code\_Err\_Cnt : data\_inout   
Major\_Frame\_Time : data\_out   
Time\_Code : data\_in   
Time\_Range\_Tol : data\_in   
Mjf\_Tossed\_Cnt : data\_in   
Current\_Time : data\_in   
Maj\_Vote\_Tol : data\_in   
Mjf\_Data\_Rate : data\_in Mjf\_Tossed\_Cnt to estimate the elapsed time from the last major frame. Add the elapsed time to Saved\_Time to get the estimated major frame time. Place the estimated major frame time into Major\_Frame\_Time.Est\_Time. Set the flag Major\_Frame\_Time.Est\_Time\_Used to "true".   
If Major\_Frame\_Time.Est\_Time\_Used is "true", then Store the Major\_Frame\_Time.Est\_Time in the Saved\_Time store.   
Else Store the Major\_Frame\_Time.Actual\_Time in the Saved\_Time store.

Output Major\_Frame\_Time.

Reusability

None.

NAME: 3.4.3

TITLE: Collect VCDU Quality and Accounting

INPUT/OUTPUT: VCDU\_QA : data\_inout Major\_Frame\_VCDU\_Set : data\_in Sub\_Intv\_Info : data\_in Valid\_CCSDS\_Parms : data\_in

BODY:   
Description of Process Collect the VCDU quality and accounting data.

## Assumptions

Preconditions Quality annotation exists in the Major\_Frame\_VCDU\_Set.Ann\_VCDU.

Postconditions The Mjf\_VCDU\_QA store will be updated with the newly calculated information.

Constraints None.

Functional Breakdown Place into VCDU\_QA.Mjf\_CADU\_Rcvd\_Cnt the Major\_Frame\_VCDU\_Set. Mjf\_CADU\_Rcvd\_Cnt. Place into VCDU\_QA.Mjf\_CADU\_Fly\_Cnt the Major\_Frame\_VCDU\_Set. Mjf\_CADU\_Fly\_Cnt. Place into VCDU\_QA.ETM\_Data\_Format the Sub\_Intv\_Info.VCID. Place into VCDU\_QA.Mjf\_CADU\_Seq\_Err\_Cnt the Major\_Frame\_VCDU\_Set. Mjf\_CADU\_Seq\_Err\_Cnt. Use Sub\_Intv\_Info.Contact\_Id to extract the RDP\_Acct.Valid\_CCSDS\_Parms and place the information into VCDU\_QA.Mjf\_CADU\_Sync\_Info. Mjf\_CADU\_Sync\_Strategy.Valid\_CCSDS\_Parms.

For each VCDU in the Major\_Frame\_VCDU\_Set, do the following: Place into the VCDU\_QA.Mjf\_CADU\_Sync\_Info.Mjf\_CADU\_Polarity with the Major\_Frame\_VCDU\_Set.Gap\_Tagged\_VCDUs. Ann\_VCDU.Sync\_Annotation.CADU\_Polarity\_Flag. Accumulate the VCDU\_QA.Mjf\_CADU\_Sync\_Info.Mjf\_CADU\_Bit\_Slip with the Major\_Frame\_VCDU\_Set.Gap\_Tagged\_VCDUs.Ann\_VCDU. Sync\_Annotation.CADU\_Bit\_Slip. Accumulate the VCDU\_QA.Mjf\_CADU\_Sync\_Err\_Cnt if the Major\_Frame\_VCDU\_Set.Gap\_Tagged\_VCDUs.Ann\_VCDU. Sync\_Annotation.CADU\_Sync\_Error\_Flag is "true" Accumulate the VCDU\_QA.Mjf\_CADU\_Missing\_Cnt with the number of missing CADUs. This count should be derived from the sequence counter. If Major\_Frame\_VCDU\_Set.Gap\_Tagged\_VCDUs.Ann\_VCDU.RS\_Annotation is "true", then

Accumulate the VCDU\_QA.Mjf\_CADU\_RS\_Corr\_Cnt.

Else

Accumulate the VCDU\_QA.Mjf\_CADU\_RS\_Uncorr\_Cnt.

If the Major\_Frame\_VCDU\_Set.Gap\_Tagged\_VCDUs.Ann\_VCDU. BCH\_Annotation.Data\_Field\_Qual\_Indicator is set to "CORRECTABLE", then Accumulate the VCDU\_QA.Mjf\_CADU\_BCH\_Corr\_Cnt.   
Else if the Major\_Frame\_VCDU\_Set.Gap\_Tagged\_VCDUs.Ann\_VCDU. BCH\_Annotation.Data\_Field\_Qual\_Indicator set to "UNCORRECTABLE", then Accumulate the VCDU\_QA.Mjf\_CADU\_BCH\_Uncorr\_Cnt.

Accumulate the VCDU\_QA.Mjf\_CADU\_BCH\_Bits\_Corr with the Major\_Frame\_VCDU\_Set.Gap\_Tagged\_VCDUs.Ann\_VCDU. BCH\_Annotation.BCH\_Bits\_Corrected.

Accumulate the VCDU\_QA.Mjf\_CADU\_CRC\_Err\_Cnt if the Major\_Frame\_VCDU\_Set.Gap\_Tagged\_VCDUs.Ann\_VCDU. CRC\_Annotation is "true".

Compute the VCDU\_QA.Mjf\_CADU\_BER\_Cnt by dividing the sum of the VCDU\_QA.Mjf\_CADU\_BCH\_Corr\_Cnt VCDU\_QA.Mjf\_CADU\_BCH\_Uncorr\_Cnt VCDU\_QA.Mjf\_CADU\_CRC\_Err\_Cnt by the Major\_Frame\_VCDU\_Set.Mjf\_CADU\_Rcvd\_Cnt multiplied by the bits per CADU

Replace the Mjf\_VCDU\_QA store with the new VCDU\_QA information.

Reusability None.

NAME: 3.4.4;11

TITLE: Determine Subintervals

INPUT/OUTPUT:   
Mjf\_Full\_Fill\_Cnt : data\_inout   
Current\_Sub\_Intv\_Id : data\_inout   
Sub\_Intv\_Id : data\_out   
Mjf\_Full\_Fill\_Cnt : data\_out   
Sub\_Intv : data\_out   
Major\_Frame\_Time : data\_in   
Sub\_Intv\_Delta : data\_in   
Sub\_Intv\_Info : data\_in   
Mjf\_Data\_Rate : data\_in   
MF\_Stop\_Time : data\_in

## BODY:

Description of Process Determine the subinterval range.

Assumptions Preconditions The Valid\_MFP\_Parms.Sub\_Intv\_Delta must exist.

Postconditions A Subinterval ID and range are generated.

Constraints None.

Functional Breakdown Retrieve the Valid\_MFP\_Parms.Sub\_Intv\_Delta value from the Valid\_MFP\_Parms data store If the Sub\_Intv data store is empty, then Generate a unique Sub\_Intv\_Id. Place the Sub\_Intv\_Id into the Current\_Sub\_Intv\_Id.

If the Sub\_Intv\_Info.VCID\_Change\_Flag is "true", then declare the start of a new subinterval. Place the Sub\_Intv\_Info.Contact\_Id into Sub\_Intv.Contact\_Id identified by Current\_Sub\_Intv\_Id. Place the Sub\_Intv\_Info.VCID into Sub\_Intv.VCID identified by Current\_Sub\_Intv\_Id. Place the Major\_Frame\_Time into Sub\_Intv.MF\_Start\_Time identified by Current\_Sub\_Intv\_Id.   
If the Sub\_Intv\_Info.End\_Of\_Contact\_Flag is "true", then declare the end of the subinterval. Place Major\_Frame\_Time into Sub\_Intv.MF\_Stop\_Time identified by Current\_Sub\_Intv\_Id.   
If no subinterval has yet been declared, then Retrieve Sub\_Intv.MF\_Stop\_Time identified by Current\_Sub\_Intv\_Id. Calculate a delta time value that is the difference between the

Major\_Frame\_Time and Sub\_Intv.MF\_Stop\_Time.

If the delta time value exceeds Valid\_MFP\_Parms.Sub\_Intv\_Delta, or the delta value is negative, then

Declare the start of a new subinterval.

Place the Sub\_Intv\_Info.Contact\_Id into Sub\_Intv.Contact\_Id identified by Current\_Sub\_Intv\_Id.

Place the Sub\_Intv\_Info.VCID into Sub\_Intv.VCID identified by Current\_Sub\_Intv\_Id.

Place the Major\_Frame\_Time into Sub\_Intv.MF\_Start\_Time identified by Current\_Sub\_Intv\_Id.

If the delta time value is less than Valid\_MFP\_Parms.Sub\_Intv\_Delta, but positive, then no subinterval is declared.

This indicates that major frames are missing.

Calculate the number of missing major frames by dividing the delta time value by Valid\_MFP\_Parms.Mjf\_Data\_Rate.

Place the result into Mjf\_Full\_Fill\_Cnt.

Accumulate the Mjf\_VCDU\_QA.Mjf\_Full\_Fill\_Cnt in the Mjf\_VCDU\_QA store

Output Mjf\_Full\_Fill\_Cnt.

NAME: 3.5.1;12

TITLE: Deinterleave and Reverse Bands

INPUT/OUTPUT:   
Mjf\_Part\_Fill\_Cnt : data\_out   
Status\_Info : data\_out   
Deinterleaved\_Band\_Data : data\_out   
Mjf\_VCDU\_Data : data\_in   
Fill\_Value : data\_in   
Scan\_Dir : data\_in

## BODY:

Description of Process Extract the detectors of each band from the minor frames of the Mjf\_VCDU\_Data.

## Assumptions

Preconditions Mjf\_VCDU\_Data is in VCDU format.

Postconditions The Deinterleaved\_Band\_Data is organized by band and detector.

Functional Breakdown Extract the Status\_Info from the PCD/Status data of the VCDU data zone. Output the Status\_Info to the IDPS. Extract the Format\_Id from the Status\_Info. Deinterleave each minor frame in the following manner according to the Status\_Info.Format\_Id, format 1 or format 2. If the Scan\_Dir is forward, then Extract each byte of each minor frame starting with the minor frame location indicated by the Mjf\_VCDU\_Data. Direction\_Start. Place into Fmt#\_Band\_Data the appropriate data area according to band width and detector number. Else Extract each byte of each minor frame starting with the last minor frame. The scene data minor frames will instead be deinterleaved from last to first, that is, in reverse order. Place into Fmt#\_Band\_Data the appropriate data area according to band width and detector number. If Mjf\_VCDU\_Data.Num\_Missing\_VCDUs is positive, then Minor frames are missing. Place Valid\_MFP\_Parms.Fill\_Value into Deinterleaved\_Band\_Data for each missing minor frame. Increment the Mjf\_VCDU\_QA.Mjf\_Part\_Full\_Cnt in the Mjf\_VCDU\_QA store.

Output Deinterleaved\_Band\_Data.

NAME: 3.5.2;10

TITLE: Align Bands

INPUT/OUTPUT:   
Aligned\_Bands : data\_out   
Deinterleaved\_Band\_Data : data\_in   
Mjf\_Full\_Fill\_Cnt : data\_in   
Fill\_Value : data\_in   
Sensor\_Alignment\_Info : data\_in   
Sub\_Intv\_Id : data\_in

## BODY:

Description of Process Align the bands according to the Valid\_MFP\_Parms.Sensor\_Alignment\_Info.

## Assumptions

Preconditions The sensor alignment info is available.

Postconditions The detectors of the Aligned\_Bands are aligned on a major frame basis.

Constraints The Valid\_MFP\_Parms.Sensor\_Alignment\_Info must exist.

Functional Breakdown Place the Sub\_Intv\_Id into Aligned\_Bands.Sub\_Intv\_Id. Determine the format type from the Deinterleaved\_Band\_Data.Format\_Id. If Mjf\_Full\_Fill\_Cnt is positive, then If the format type is 1, Fill the Aligned\_Bands.Fmt1\_Align\_Data with the Fill\_Value. Else Fill the Aligned\_Bands.Fmt2\_Align\_Data with the Fill\_Value. Output Aligned\_Bands for each Mjf\_Full\_Fill\_Count. If the format type is 1, Align the Deinterleaved\_Band\_Data.Fmt1\_Band\_Data using the Valid\_MFP\_Parms.Sensor\_Alignment\_Info for format 1 type data. Place the aligned data into Aligned\_Bands.Fmt1\_Align\_Data. Else Align the Deinterleaved\_Band\_Data.Fmt2\_Band\_Data using the Valid\_MFP\_Parms.Sensor\_Alignment\_Info for format 2 type data. Place the aligned data into Aligned\_Bands.Fmt2\_Align\_Data. Output Aligned\_Bands.

Reusability None.

NAME: 3.6.1;11

TITLE: Create MSCD File

INPUT/OUTPUT: MSCD\_Data : data\_inout Sub\_Intv\_Id : data\_out MSCD\_File\_Name : data\_out MFP\_MSCD\_Status : data\_out MSCD\_File : data\_out MF\_Start\_Time : data\_in File\_Version\_Number : data\_in Sub\_Intv\_Id : data\_in

## BODY:

Description of Process Creates the MSCD\_File\_Name for the MSCD\_File for each subinterval. Stores MSCD\_Data in the MSCD\_File for each subinterval.

## Assumptions

Preconditions The Sub\_Intv\_Id is received.

## Postconditions

The MSCD\_File\_Name and MSCD\_File is created for each subinterval.   
Emptys the MSCD\_Data store after each subinterval.   
Send MFP\_Status.MFP\_MSCD\_Status to MACS.   
The MSCD\_File\_Name is placed into the MFP\_Acct store associated with a particular subinterval

Constraints None.

## Functional Breakdown

Create the MSCD\_File\_Name using LPS\_Configuration.File\_Version\_Number and Sub\_Intv.MF\_Start\_Time identified by Sub\_Intv\_Id.   
Receive the MSCD\_Data, which is the FHS\_Err, SHS\_Err, and Scan\_Dir extracted from Mjf\_VCDU\_Data, and write the data to the MSCD\_File.   
Update the MFP\_Acct store to contain the MSCD\_File\_Name for the subinterval identified by Sub\_Intv\_Id.   
Send any MFP\_Status.MFP\_MSCD\_Status to MACS.   
Clear MSCD\_Data store (to receive the next subinterval of MSCD\_Data).

Reusability This process may be used to create the Cal\_File.

NAME: 3.6.2;12

TITLE: Create Calibration File

## INPUT/OUTPUT:

Cal\_Data : data\_inout Sub\_Intv\_Id : data\_out Cal\_File\_Name : data\_out MFP\_Cal\_Status : data\_out Cal\_File : data\_out MF\_Start\_Time : data\_in Sub\_Intv\_Id : data\_in File\_Version\_Number : data\_in

## BODY:

Description of Process Creates the Cal\_File\_Name and the Cal\_File for each subinterval. Stores the Cal\_Data in the Cal\_File for each subinterval.

## Assumptions

Preconditions The Sub\_Intv\_Id is received.

## Postconditions

The Cal\_File\_Name and the Cal\_File is created for each subinterval.   
Emptys the Cal\_Data store after each subinterval.   
Send MFP\_Status.MFP\_Cal\_Status to MACS.   
The Cal\_File\_Name is placed into the MFP\_Acct store associated with a particular subinterval

Constraints None.

## Functional Breakdown

Create the Cal\_File\_Name using LPS\_Configuration.File\_Version\_Number and Sub\_Intv.MF\_Start\_Time identified by Sub\_Intv\_Id.   
Receive the Cal\_Data and write the data to the Cal\_File.   
Update the MFP\_Acct store to contain the Cal\_File\_Name for the subinterval identified by Sub\_Intv\_Id.   
Send any MFP\_Status.MFP\_Cal\_Status to MACS.   
Clear the Cal\_Data store (to receive the next subinterval of Cal\_Data).

## Reusability

This process can be used to create the MSCD\_File.

NAME: 3.6.3;10

TITLE: Extract MSCD Data

INPUT/OUTPUT: Scan\_Dir : data\_out MSCD\_Data : data\_out Mjf\_VCDU\_Data : data\_in

BODY:   
Description of Process Extracts the MSCD\_Data from the Mjf\_VCDU\_Data and sends the MSCD\_Data to the MSCD\_Data store.

## Assumptions

Preconditions The Mjf\_VCDU\_Data is received.

Postconditions The MSCD\_Data are extracted from the Mjf\_VCDU\_Data for a subinterval. The MSCD\_Data is sent to the MSCD\_Data store.

Constraints None.

Functional Breakdown Starting after the Mjf\_VCDU\_Data.End\_Of\_Line, extract five data words from each of the first 12 groups in minor frame 1.

Extract five data words from groups 13, 14, 15, and 16 from minor frame 1. Perform a majority vote on each data word group. This is the SHS\_Err.

Extract five data words from groups 1 through 8 from minor frame 2.   
Perform a majority vote on each data word group. This is the FHS\_Err. Extract five data words from groups 9 through 16 of minor frame 2.   
Perform a majority vote on each data word group. This is the Scan\_Dir.

If the Scan\_Dir is 0 then the scan direction is reverse else if the Scan\_Dir is 1 then the scan direction is forward.

Append the Scan\_Dir, FHS\_Err, and SHS\_Err to the MSCD\_Data store.   
Output the Scan\_Dir.

## Reusability

Use the majority vote of data words from the parse major frame process to extract the MSCD\_Data.

NAME: 3.6.4;12

TITLE: Extract Calibration Data

INPUT/OUTPUT:   
Cal\_Data : data\_out   
Mjf\_VCDU\_Data : data\_in   
Fill\_Value : data\_in   
Sensor\_Alignment\_Info : data\_in   
BODY:   
Description of Process Extracts the Cal\_Data from the Mjf\_VCDU\_Data for each subinterval.

## Assumptions

Preconditions The Mjf\_VCDU\_Data is received.

Postconditions The deinterleaved Cal\_Data is stored in the Cal\_Data store for a subinterval.

Constraints None.

## Functional Breakdown ional Breakdown

Search for the end of mirror scan correction data in Mjf\_VCDU\_Data.   
Starting after the end of the mirror scan correction data, Extract the Cal\_Data on a minor frame basis.   
Extract the scan bit.   
If the scan bit is forward, then Deinterleave the Cal\_Data starting with the location indicated by Mjf\_VCDU\_Data.Direction\_Start   
Else Deinterleave the Cal\_Data in reverse order by locating where the start of the Cal\_Data (using Mjf\_VCDU\_Data.Direction\_Start) to the end of the Cal\_Data going backwards.   
Check the Mjf\_VCDU\_Data.Gap\_Tagged\_VCDUs.Num\_Missing\_VCDUs   
If there are missing VCDUs, then Fill the missing VCDUs with Valid\_MFP\_Parms.Fill\_Value   
If the deinterleaved Cal\_Data is format 1, then Align the deinterleaved Cal\_Data using Valid\_MFP\_Parms. Sensor\_Alignment\_Info for format 1. Append the deinterleaved and aligned Cal\_Data to the Cal\_Data store according to band width and detector number.   
Else Align the deinterleaved Cal\_Data using Valid\_MFP\_Parms. Sensor\_Alignment\_Info for format 2. Append the deinterleaved and aligned Cal\_Data to the Cal\_Data store according to band width and detector number.

Reusability

Uses portions of the Deinterleave and Reverse Bands and Align Bands procedure from the Generate Band Data process.

NAME: 3.7;15

TITLE: Generate Level 0R QA Report

INPUT/OUTPUT: Report\_MFP\_L0R\_QA : data\_out Mjf\_VCDU\_QA\_Report\_Info : data\_in MFP\_Rpt\_L0R\_QA\_Drct : data\_in MF\_Start\_Time : data\_in MF\_Stop\_Time : data\_in

BODY:   
Description of Process Upon receipt of a report request, generate reports.

## Assumptions

Preconditions There must be data in MFP\_Acct.Mjf\_VCDU\_QA.

Postconditions A Level 0R quality and accounting report on a subinterval basis is generated.

Constraints None.

## Functional Breakdown

Use the MFP\_Rpt\_L0R\_QA\_Drct.Sub\_Intv\_Id to retrieve the following information:

Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_Count, Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_Sync\_Info, Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_Sync\_Err\_Cnt, Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_Rcvd\_Cnt, Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_Fly\_Cnt, Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_Missing\_Cnt, Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_RS\_Corr\_Cnt, Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_RS\_Uncorr\_Cnt, Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_BCH\_Corr\_Cnt, Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_BCH\_Uncorr\_Cnt, Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_CRC\_Err\_Cnt, Mjf\_VCDU\_QA.Mjf\_QA.Mjf\_Full\_Fill\_Cnt, Mjf\_VCDU\_QA.Mjf\_QA.Mjf\_Part\_Fill\_Cnt, Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_BER\_Cnt,

into the Report\_MFP\_L0R\_QA.Mjf\_VCDU\_QA\_Report\_Info

Sub\_Intv.MF\_Start\_Time, and Sub\_Intv.MF\_Stop\_Time

into the Report\_MFP\_L0R\_QA.

Create the report format for the Report\_MFP\_L0R\_QA.

Output the Report\_MFP\_L0R\_QA.

Report generation routines exist within Oracle.

NAME: 3.8

TITLE: Collect Quality and Accounting

INPUT/OUTPUT: Mjf\_VCDU\_QA : data\_inout Mjf\_VCDU\_QA : data\_out MFP\_Mjf\_Status : data\_out Sub\_Intv\_Id : data\_out Valid\_MFP\_Thres : data\_in Sub\_Intv\_Id : data\_in

## BODY:

Description of Process Collect the Mjf\_VCDU\_QA data, check threshold values, and place the information into the accounting store on a subinterval basis.

## Assumptions

Preconditions Mjf\_VCDU\_QA has quality and accounting data on a major frame basis.

Postconditions The Mjf\_VCDU\_QA is placed into the MFP\_Acct store with NULL values for the MSCD\_File\_Name and Cal\_File\_Name on a subinterval basis.

Constraints None.

## Functional Breakdown

Upon receipt of the Sub\_Intv\_Id,   
Extract the information out of Mjf\_VCDU\_QA and place into the MFP\_Acct store identified by Sub\_Intv\_Id.   
Test for the following thresholds: If Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_Seq\_Err\_Cnt exceeds Valid\_MFP\_Thres.Mjf\_CADU\_Seq\_Err\_Thr, then Add an error message to MFP\_Status.MFP\_Mjf\_Status. If Mjf\_VCDU\_QA.Mjf\_QA.Mnf\_Ctr\_Err exceeds Valid\_MFP\_Thres. Mnf\_Ctr\_Thr, then Add an error message to MFP\_Status.MFP\_Mjf\_Status. If Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_Sync\_Err\_Cnt exceeds Valid\_MFP\_Thres.Sync\_Thr, then Add an error message to MFP\_Status.MFP\_Mjf\_Status. If Mjf\_VCDU\_QA.Mjf\_QA.Mjf\_Eol\_Err\_Cnt exceeds Valid\_MFP\_Thres. Eol\_Thr, then Add an error message to MFP\_Status.MFP\_Mjf\_Status. If Mjf\_VCDU\_QA.Mjf\_Time\_Code\_Err\_Cnt exceeds Valid\_MFP\_Thres. Tc\_Thr, then Add an error message to MFP\_Status.MFP\_Mjf\_Status. If Mjf\_VCDU\_QA.Mjf\_Full\_Fill\_Cnt exceeds Valid\_MFP\_Thres. Full\_Mjf\_Thr, then Add an error message to MFP\_Status.MFP\_Mjf\_Status.

If Mjf\_VCDU\_QA.Mjf\_Part\_Fill\_Cnt exceeds Valid\_MFP\_Thres.

Part\_Mjf\_Thr, then

Add an error message to MFP\_Status.MFP\_Mjf\_Status.

If any error messages are in MFP\_Status.MFP\_Mjf\_Status, then

Output MFP\_Status.MFP\_Mjf\_Status.

Empty the Mjf\_VCDU\_QA store of all data pertaining to the new subinterval.

Reusability

None.

## 4.6.2 Performance Requirements

The following list summarizes the performance requirements allocated to the MFPS:

4.6.2.1 The MFPS software on each LPS string shall provide the capability to process the equivalent of any combination of the format 1 and format 2 portions of 125 Landsat 7 ETM+ scenes of wideband data per day (approximately 25-30 GB per day).

4.6.2.2 The MFPS software on each LPS string shall process received data at a minimum rate of not less than 7.5 Mbps. (based on a minimum raw wideband throughput of 7.5 Mbps).

4.6.2.3 The MFPS software on each LPS string shall provide the capability to execute concurrently with all other LPS subsystems.

4.6.2.3.1 The MFPS software shall begin to process received raw data immediately upon receipt of required inputs.

4.6.2.3.2 The MFPS software shall output the equivalent of one Landsat 7 ETM+ scene worth's of Major Frames and PCD within 240 seconds of the receipt of all required inputs.

4.6.2.4 The MFPS software on each LPS string shall provide the capability to reprocess a maximum of 10% of a string's daily input volume of wideband data (approximately 12.5 scenes or 2.5-3 GB per day).

4.6.2.5 The MFPS software on each LPS string shall provide the capability to process received wideband data at a daily average aggregate rate of 3 megabits per second (Mbps) (Includes 10% of overhead due to reprocessing).

4.6.2.6 The MFPS software on each LPS string shall maintain data processing throughput performance for all Landsat 7 raw wideband data received with a BER of one bit error in 105 bits, without loss of level zero R processed data and without retransmission.

4.6.2.7 The MFPS software on each LPS string shall output any periodic processing status information that it generates with a maximum latency of 30 seconds between outputs.

## 4.7 Payload Correction Data Subsystem (PCDS)

The PCDS is responsible for building PCD major frames using the PCD information words taken from the PCD/Status section of the virtual channel data unit (VCDU). The PCD major frames contain data that is needed to geometrically correct the ETM+ imagery. In addition, the PCDS identifies all Enhanced Thematic Mapper Plus (ETM+) scenes in accordance with the Worldwide Reference System (WRS) on a subinterval basis.

## 4.7.1 Functional Requirements

The following list summarizes the functional requirements allocated to the PCDS:

• validate and store the processing parameters received from MACS.

• provide the capability to synchronize on PCD bytes for assembling PCD minor frames, using fill for missing PCD data. Assemble PCD major frames using the PCD minor frames.

• provide the capability to generate PCD file(s) on a subinterval basis.

• provide the capability to collect and store PCD quality and accounting and processed PCD quality and accounting data on a subinterval basis.

• provide the capability to perform ETM+ scene identification within an accuracy of 1 kilometer in accordance with the Worldwide Reference System (WRS) scheme.

• calculate the spacecraft drift time based on information available in the PCD.

• provide the capability to identify the presence of calibration door activities.

• allow the operator to select thresholds for results and errors reported by the LPS. Using the thresholds, automatically generate messages and alarms to alert the operator of LPS results and errors exceeding selected thresholds.

## 4.7.1.1 Major Functions

The PCDS accepts the PCD\_Info from the Major Frame Processing Subsystem. PCDS extracts the PCD information words from the PCD\_Info that will be used to build PCD minor frames. If any of the PCD information words are missing, then fill will be used in place of the missing information word. The PCD minor frame accounting is generated on a subinterval basis.

The PCD minor frames are used to build PCD major frames. PCD major frame quality and accounting is generated per PCD major frame. Four consecutive PCD major frames are grouped into a Full\_PCD\_Cycle. The Full\_PCD\_Cycles are used to build the PCD\_File on a subinterval basis.

In addition, PCDS uses the Full\_PCD\_Cycles to extract the drift time for use by the Image Data Processing Subsystem (IDPS) on a subinterval basis. The PCDS identifies the ETM+ scenes using the Full\_PCD\_Cycles in accordance with the Worldwide Reference System (WRS) scheme, and provides the scene parameters, per scene, on a subinterval basis.

The major functions of PCDS are depicted in the following data flow diagrams.

Figure 4-11   
PCDS - DFD 4.0   
Figure 4-12   
PCDS - DFD 4.2   
Figure 4-13   
PCDS - DFD 4.3   
Figure 4-14   
PCDS - DFD 4.4

## 4.7.1.2 Interface Requirements

The following two tables summarize the interface requirements for the PCDS:  
Table 4.7 PCDS Interface Requirements - INPUT
<table><tr><td rowspan=1 colspan=1>Input Item Name</td><td rowspan=1 colspan=1>Source</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>PCD_Thresholds</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Thresholds used by PCDS</td></tr><tr><td rowspan=1 colspan=1>PCD_Parms</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Parameters used by PCDS.</td></tr><tr><td rowspan=1 colspan=1>LPS_Configuration</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>String specific information.</td></tr><tr><td rowspan=1 colspan=1>Current_Time</td><td rowspan=1 colspan=1>TimeSource</td><td rowspan=1 colspan=1>System wide time source</td></tr><tr><td rowspan=1 colspan=1>Major_Frame_Time</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>The time associated with onemajor frame.</td></tr><tr><td rowspan=1 colspan=1>PCD_Info</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>The PCD words and informationneeded to process PCD data.</td></tr><tr><td rowspan=1 colspan=1>Sub_Intv</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>The beginning and ending majorframe times corresponding to apredefined Sub_Intv time range.</td></tr><tr><td rowspan=1 colspan=1>WRS_Table_Info</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>The WRS scheme values.</td></tr></table>

Table 4.8 PCDS Interface Requirements - OUTPUT
<table><tr><td rowspan=1 colspan=1>Output Item Name</td><td rowspan=1 colspan=1>Destination</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>Scene_Info</td><td rowspan=1 colspan=1>IDPS</td><td rowspan=1 colspan=1>The scene identification inaccordance with the WorldwideReference System (WRS) scheme</td></tr><tr><td rowspan=1 colspan=1>PCD_File</td><td rowspan=1 colspan=1>LDTS</td><td rowspan=1 colspan=1>A file containing the PCD MajorFramesreceivedduringasubinterval, on a full PCD Cyclebasis.</td></tr><tr><td rowspan=1 colspan=1>PCD_Acct</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>The statistics that are gatheredfrom the processing of PCD_Info.</td></tr><tr><td rowspan=1 colspan=1>Drift_Time</td><td rowspan=1 colspan=1>IDPS</td><td rowspan=1 colspan=1>The equation that provides thedifference between the spacecrafttime and the actual time of theETM+ major frame.</td></tr><tr><td rowspan=1 colspan=1>PCD_Setup_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>The status of validating the PCDparameters and threshoǐds.</td></tr><tr><td rowspan=1 colspan=1>[PCD_Assemble_Cycle_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Errors that are detected duringthe processing of PCD data.</td></tr></table>

## 4.7.1.3 Detailed Functional Requirements

This section contains the process specifications for the lowest level processes in the PCDS data flow diagrams.

NAME: 4.1;15

TITLE: Validate PCD Parameters

## INPUT/OUTPUT:

Valid\_WRS\_Parms : data\_out Valid\_Scene\_Parms : data\_out PCD\_Setup\_Status : data\_out Valid\_PCD\_Thres : data\_out Valid\_PCD\_Parms : data\_out PCD\_Parms : data\_in PCD\_Thresholds : data\_in Current\_Time : data\_in

## BODY:

Description of Process Validate PCD Parameters validates and stores user input parameters that are used to process PCD data.

## Assumptions

Preconditions None.

Postconditions MACS is notified if there are invalid parameters or thresholds.

Constraints The parameters must conform to predefined thresholds The processing of data for a contact period will not be interrupted to process updates to the parameters and thresholds.

## Functional Breakdown

Validate that PCD\_Thresholds are within the following limits: PCD\_Directive.PCD\_Thresholds.Att\_Lower\_Bounds < PCD\_Directive.PCD\_Thresholds.Att\_Upper\_Bounds PCD\_Directive.PCD\_Thresholds.Ephem\_Position\_Lower < PCD\_Directive.PCD\_Thresholds.Ephem\_Position\_Upper PCD\_Directive.PCD\_Thresholds.Ephem\_Velocity\_Lower < PCD\_Directive.PCD\_Thresholds.Ephem\_Velocity\_Upper PCD\_Directive.PCD\_Thresholds.Num\_Failed\_Votes >0 PCD\_Directive.PCD\_Thresholds.Num\_Missing\_Data\_Words >0 Store the validated PCD\_Thresholds entries in Valid\_PCD\_Thres.

Validate that PCD\_Parms entries are within the following limits: PCD\_Directive.PCD\_Parms.Frame\_Fill\_Values >=0 Store the validated PCD\_Parms entries in Valid\_PCD\_Parms.

## Validate that the scene setup PCD\_Parms entries are within the following limits:

PCD\_Directive.PCD\_Parms.ETM\_Plus\_To\_Body\_Trans >=-1 and <=1 PCD\_Directive.PCD\_Parms.Time\_Per\_Orbit > 0 PCD\_Directive.PCD\_Parms.Mission\_Start\_Time >= Current\_Time

PCD\_Directive.PCD\_Parms.ETM\_Plus\_LOS\_x >=TBD PCD\_Directive.PCD\_Parms.ETM\_Plus\_LOS\_y >=TBD PCD\_Directive.PCD\_Parms.ETM\_Plus\_LOS\_z >=TBD PCD\_Directive.PCD\_Parms.Semi\_Major\_Axis >=0 PCD\_Directive.PCD\_Parms.Semi\_Minor\_Axis >=0 Store the valid scene setup PCD\_Parms entries in Valid\_Scene\_Parms.

Validate that WRS PCD\_Parms entries are within the following limits: PCD\_Directive.PCD\_Parms.WRS\_Row\_Nominal 0 to 248 PCD\_Directive.PCD\_Parms.Latitude >=-90 and <=90 For each path corresponding to the row verify that: PCD\_Directive.PCD\_Parms.WRS\_Path\_Nominal 0 to 233 PCD\_Directive.PCD\_Parms.Longitude >=-180 and <=180 Calculate Upper\_Left\_Corner\_Latitude, Calculate Upper\_Left\_Corner\_Longitude, Calculate Upper\_Right\_Corner\_Latitude, Calculate Upper\_Right\_Corner\_Longitude, Calculate Lower\_Left\_Corner\_Latitude, Calculate Lower\_Left\_Corner\_Longitude, Calculate Lower\_Right\_Corner\_Latitude, and Calculate Lower\_Right\_Corner\_Longitud. Store the validated PCD\_Parms and calculated data entries in Valid\_WRS\_Parms.

Send a message to the MACS specifying the names and values of any parameters or thresholds that are in error. (PCD\_Status.PCD\_Setup\_Status)

Reusability

None.

NAME: 4.2.1;4

TITLE: Extract Info Word

INPUT/OUTPUT:   
PCD\_Info : data\_in   
Partial\_Rep\_Info\_Word : data\_inout   
Rep\_Info\_Word : data\_out   
BODY:   
Description of Process Extract Info Word extracts the triplicate PCD information word from the PCD\_Info.PCD\_Byte stream.

## Assumptions

Preconditions The first four PCD bytes have been extracted from the PCD/Status section of every VCDU and passed to the PCDS. A count of missing VCDUs must be provided by the Major Frame Processing Subsystem (MFPS). A token indicating the end of a contact period must be provided by the MFPS immediately after all PCD\_Bytes for the contact period has been sent.   
Post conditions The bytes following the information word sync pattern will be stored as a Partial\_Rep\_Info\_Word, if necessary, until three words have been obtained and assigned to Rep\_ Info\_Word. If VCDUs are missing, then the Rep\_Info\_Word.Info\_Word\_Missing value is set to reflect the number of missing information words.   
Constraints None.

Functional Breakdown Search the PCD\_Info.PCD\_Bytes for an information word sync pattern (0x16) which identifies the beginning of a PCD Data Word Cycle.

Maintain a count of the number of words received for each PCD Data Word Cycle.

If an information word sync pattern is found, inspect the next three words for a fill word pattern (0x32) followed by another information word sync pattern (0x16).

If the fill-sync pattern is found within the three words then use any data word(s) that occur prior to the fill-sync pattern, assign null value(s) to the information words that were not available for the Rep\_Info\_Word and increment the Rep\_Info\_Word.Info\_Word\_Missing.

If the fill-sync pattern is not found within the three words then extract the three data words and store as Rep\_Info\_Word. The Rep\_Info\_ Word.Info\_Word\_Missing is assigned a value that reflects the number of information words that were not available.

If PCD\_Info.Num\_Missing\_VCDUs indicates that missing VCDUs were encountered and the number of words received per PCD Data Word Cycle exceeds

nine (9) then assign a Null value to the three information words of Rep\_Info\_Word and increment Rep\_Info\_Word.Info\_Word\_Missing.

If PCD\_Info.End\_Of\_Contact\_Flag indicates that the contact period has ended, then

Retrieve any data contained in Partial\_Rep\_Info\_Word and assign them to Rep\_Info\_Word.

If the number of remaining Partial\_Rep\_Info\_Word is < 3 then assign a null value to Rep\_Info\_Word to represent the missing information word(s).

Assign a value to Rep\_Info\_Word.Info\_Word\_Missing that reflects the number of missing information words.

If the number of remaining Partial\_Rep\_Info\_Word is = 3 then assign the Partial\_Rep\_Info\_Word to Rep\_Info\_Word.

Set Rep\_Info\_Word.Contact\_Ended.

Place the PCD\_Info.Sub\_Intv\_Id into the Rep\_Info\_Word.Sub\_Intv\_Id.   
Output Rep\_Info\_Word.

## Reusability

None.

NAME: 4.2.2;5

TITLE: Determine Majority Info Word

INPUT/OUTPUT: PCD\_Info\_Word : data\_out Rep\_Info\_Word : data\_in

## BODY:

Description of Process Determine Majority Info Word derives the PCD\_Info\_Word from the Rep\_ Info\_Word.

## Assumptions

Preconditions The value of Failed\_PCD\_Votes is equal to the number of failed attempts to obtain a majority information word for the current Sub\_Intv.

Post conditions None.

Constraints None.

## Functional Breakdown

If Rep\_Info\_Word.Contact\_Ended is set then set the PCD\_Info\_Word.Flush Minor\_Frames.

If the Rep\_Info\_Word.Info\_Word\_Missing value indicates that each of the three information words are missing then set the PCD\_Info\_Word. Info\_Word\_Missing value to one and assign a null value to the PCD\_Info\_Word.Info\_Word.

If the Rep\_Info\_Word.Info\_Word\_Missing value is >=1<3 then assign zero to PCD\_Info\_Word.Info\_Word\_Missing and assign (TBD) word from Rep\_Info\_Word to PCD\_Info\_Word.Info\_Word.

If Rep\_Info\_Word.Info\_Word\_Missing indicates that there are no missing information words then perform a majority vote using Rep\_Info\_ Word.Info\_Word\_1, Rep\_Info\_Word.Info\_Word\_2, and Rep\_Info\_Word. Info\_Word\_3. The majority word will be assigned to the PCD\_Info\_ Word.Info\_Word.

If all three values of Rep\_Info\_Word are different then set PCD\_Info\_Word. Majority\_Vote\_Failure. Assign (TBD) word of Rep\_Info\_Word to PCD\_ Info\_Word.Info\_Word.

Place the Rep\_Info\_Word.Sub\_Intv\_Id into the PCD\_Info\_Word.Sub\_Intv\_Id.   
Output PCD\_Info\_Word.

## Reusability

None.

NAME: 4.3.1

TITLE: Assemble Minor Frames

INPUT/OUTPUT:   
Failed\_Votes : data\_inout   
Partial\_PCD\_Minor\_Frame : data\_inout   
Sub\_Intv\_Id : data\_out   
PCD\_Assemble\_Cycle\_Status : data\_out   
PCD\_Minor\_Frame : data\_out   
Minor\_Frame\_Acct : data\_out   
PCD\_Info\_Word : data\_in   
Valid\_PCD\_Thres : data\_in   
PCD\_Frame\_Fill : data\_in

## BODY:

Description of Process Assemble Minor Frames builds the PCD\_Minor\_Frames using the PCD\_Info\_ Word and calculates the Minor Frame related statistics.

## Assumptions

Preconditions A predefined value that represents missing VCDUs and failed attempts to perform a majority vote must exist.

Post conditions None.

Constraints None.

Functional Breakdown If the PCD\_Info\_Word.Info\_Word\_Missing indicates that a valid information word is available then append PCD\_Info\_Word. Info\_Word to the current Partial\_PCD\_Minor\_Frame. If the PCD\_Info\_Word.Info\_Word\_Missing indicates that a valid information word is not available then append a predefined fill pattern, Valid\_PCD\_Parms.PCD\_Frame\_Fill, to the current Partial\_PCD\_Minor\_Frame. If the PCD\_Info\_Word.Flush\_Minor\_Frame.Contact\_Ended flag indicates that the contact period has ended, then Use Valid\_PCD\_Parms.PCD\_Frame\_Fill to complete the current Partial\_PCD\_Minor\_Frame. Output the completed PCD\_Minor\_Frame followed by a PCD\_Minor\_Frame that has a null value, which indicates that the contact period has ended. If the PCD\_Info\_Word is a PCD\_Minor\_Frame.Info\_Word.Sync\_Word, and the next two PCD\_Info\_Words are PCD\_Minor\_Frame.Info\_Word. Sync\_Word, then Use Valid\_PCD\_Parms.PCD\_Frame\_Fill to complete the current Partial\_PCD\_Minor\_Frame Output the PCD\_Minor\_Frame.

Initialize the Partial\_PCD\_Minor\_Frame   
Append the three PCD\_Minor\_Frame.Info\_Word.Sync\_Word to the new Partial\_PCD\_Minor\_Frame.   
Calculate the number of missing information words by accumulating the PCD\_Info\_Word.Info\_Word\_Missing.   
If the number of missing data words exceeds the Valid\_PCD\_Thresh.Num\_Missing\_Data\_Words then generate PCD\_Errors.Data\_Missing\_Message and send to MACS.

Calculate the number of PCD Minor Frames that have sync errors and store as Minor\_Frame\_Acct.Num\_PCD\_MNF\_Sync\_Errors.

Calculate the number of PCD Minor Frames that have been filled and store as Minor\_Frame\_Acct.Num\_PCD\_Filled\_MNF.

Calculate the number of Failed\_Votes accumulating the PCD\_Info\_Word. Majority\_Vote\_Failure flags and store as Minor\_Frame\_Acct. Failed\_PCD\_Votes. Output the Minor\_Frame\_Acct

If the number of Failed\_Votes exceeds the Valid\_PCD\_Thresh.Num\_Failed\_Votes then generate a PCD\_Status. PCD\_Assemble\_Cycle\_Status.Failed\_Votes\_Message and send to MACS.   
Output the PCD\_Info\_Word.Sub\_Intv\_Id.

Reusability None.

NAME: 4.3.2;7

TITLE: Assemble Major Frames

INPUT/OUTPUT: Partial\_PCD\_Major\_Frame : data\_inout PCD\_Major\_Frame : data\_out Major\_Frame\_Acct : data\_out PCD\_Minor\_Frame : data\_in Valid\_PCD\_Parms : data\_in

BODY:   
Description of Process Assemble Major Frames builds the PCD\_Major\_Frame using an accumulation of each PCD\_Minor\_Frame.

## Assumptions

The Major Frame Id of the first PCD Minor Frame of every PCD Major Frame will be used as the key value for the entire PCD Major Frame. Future Major Frame Ids within the PCD Major Frame will be compared to the Major Frame Id of the first PCD Minor Frame.   
If a predefined fill pattern occupies word 65 in the PCD Minor Frame then the PCD Minor Frame will be included in the building of the current PCD Major Frame.   
A predefined pattern that indicates missing PCD Minor Frames must exist in data store.   
Predefined quality indicators for ephemeris data points and attitude data points must exist in a data store.

Post conditions None.

Constraints None.

Functional Breakdown If the value of the PCD\_Minor\_Frame is null then use Valid\_PCD\_Parms.PCD\_Frame\_Fill to complete the current Partial\_PCD\_Major\_Frame. Output the completed PCD\_Major\_Frame followed by a PCD\_Major\_Frame with a null value to indicate that the contact period has ended. Compare the PCD\_Minor\_Frame.Info\_Word.Major\_Frame\_Id in word 65 of the new PCD\_Minor\_Frame to the Partial\_PCD\_Major\_Frame. PCD\_Minor\_Frame.Info\_Word.Major\_Frame\_Id Word 65 to determine if the new PCD\_Minor\_Frame belongs to the current Partial\_PCD\_ Major\_Frame. If the new PCD\_Minor\_Frame belongs to the current Partial\_PCD\_Major\_ Frame, then Append the new PCD\_Minor\_Frame to the current Partial\_PCD\_

Major\_Frame.

If the new PCD\_Minor\_Frame does not belong to the current Partial\_PCD\_ Major\_Frame, then

Use Valid\_PCD\_Parms.PCD\_Frame\_Fill to complete the current Partial\_PCD\_Major\_Frame.

Output the completed PCD\_Major\_Frame.

Append the new PCD\_Minor\_Frame to a new Partial\_PCD\_Major\_Frame.

Evaluate the ephemeris and attitude data points of each PCD\_Major\_Frame

to determine the quality using

Valid\_PCD\_Parms.Ephem\_Position\_Upper,

Valid\_PCD\_Parms.Ephem\_Position\_Lower,

Valid\_PCD\_Parms.Ephem\_Velocity\_Upper,

Valid\_PCD\_Parms.Ephem\_Velocity\_Lower,

Valid\_PCD\_Parms.Att\_Lower\_Bounds,

Valid\_PCD\_Parms.Att\_Upper\_Bounds

as thresholds to determine the number of rejected ephemeris and attitude data points and store in Major\_Frame\_Acct.Num\_

Rejected\_ADP and Major\_Frame\_Acct.Num\_Rejected\_EDP.

Calculate the number of PCD Major Frames that contain a Valid\_PCD\_Parms.

PCD\_Frame\_Fill and store as Major\_Frame\_Acct.Num\_PCD\_Filled\_MJF.

Calculate the number of missing ephemeris and attitude data points and store in Major\_Frame\_Acct.Num\_Avail\_ADP.

Calculate the number of available ephemeris and attitude data points and store in Major\_Frame\_Acct.Num\_Avail\_EDP.

Reusability

None.

NAME: 4.3.3;12

TITLE: Build PCD Cycles

INPUT/OUTPUT: Cycle\_Acct : data\_inout Partial\_PCD\_Cycle : data\_inout Full\_PCD\_Cycle : data\_out PCD\_Frame\_Info : data\_out Minor\_Frame\_Acct : data\_in Major\_Frame\_Acct : data\_in PCD\_Major\_Frame : data\_in PCD\_Frame\_Fill : data\_in Sub\_Intv\_Id : data\_in

## BODY:

Description of Process Build PCD Cycles uses PCD\_Major\_Frame to build a Full\_PCD\_Cycle. The PCD\_Frame\_Info is collected and reported for each Full\_PCD\_Cycle on a subinterval basis.

## Assumptions

Preconditions None.

Post conditions Partial PCD Cycles will be filled using a PCD\_Frame\_Fill.(TBR).

Constraints None.

Functional Breakdown Place the Sub\_Intv\_Id into the Full\_PCD\_Cycle.Sub\_Intv\_Id. Collect Minor\_Frame\_Acct which is received on a PCD Minor Frame basis and store the information into the Cycle\_Acct store. Collect Major\_Frame\_Acct which is received on a PCD Major Frame basis and store the information into the Cycle\_Acct store. Use the PCD\_Major\_Frame.PCD\_Minor\_Frame.Info\_Word.Major\_Frame\_Id word 65 to determine the Major\_Frame\_Id. If the Major\_Frame\_Id indicates that the PCD\_Major\_Frame is part of the current Partial\_PCD\_Cycle then append the PCD\_Major\_Frame to the current Partial\_PCD\_Cycle. If the Major\_Frame\_Id indicates that the PCD\_Major\_Frame is not part of the current Partial\_PCD\_Cycle then use PCD\_Frame\_Fill to complete the current Partial\_PCD\_Cycle. Place the Partial\_PCD\_Cycle into the Full\_PCD\_Cycle Output the Full\_PCD\_Cycle. If the Major\_Frame\_Id contains a value of zero then start a new Partial\_PCD\_Cycle, appending the current PCD\_Major\_Frame. If the Major\_Frame\_Id contains a value other than zero then discard the current PCD\_Major\_Frame. If the PCD\_Major\_Frame has a null value then the current Partial\_PCD\_Cycle

will be completed using PCD\_Frame\_Fill.

A Full\_PCD\_Cycle will be generated with a null value to indicate that the contact period has ended.   
Output the Full\_PCD\_Cycle.

Format the Cycle\_Acct and store as PCD\_Frame\_Info for the Full\_PCD\_Cycle and assign the Sub\_Intv\_Id to PCD\_Frame\_Info.Sub\_Intv\_Id.

Store the PCD\_Frame\_Info in PCD\_Acct identified by Sub\_Intv\_Id.

Reusability

None.

NAME: 4.4.1;13

TITLE: Compute Position MJF Time

INPUT/OUTPUT:   
Cal\_Info : data\_inout   
MJF\_Time\_And\_Position : data\_inout   
Major\_Frame\_Time : data\_in   
Full\_PCD\_Cycle : data\_in   
MF\_Start\_Time : data\_in   
MF\_Stop\_Time : data\_in

## BODY:

Description of Process Compute Position MJF Time computes the ETM+ Major Frame Time for each position within the Full\_PCD\_Cycle and determines the calibration door activity status for each position.

## Assumptions

Preconditions A predefined, fixed time length indicating the period of time between the generation of PCD Major Frames must exist.

Interpolated attitude and ephemeris data points will not be included in the PCD\_File but will be used for latitude and longitude calculations.   
The Cal\_Info.Calibration\_Door\_Activity\_Status is the same for each PCD\_Major\_Frame within a Full\_PCD\_Cycle.

If the spacecraft time of the Full\_PCD\_Cycle is greater than the corresponding Sub\_Intv.MF\_Stop\_Time then the Full\_PCD\_Cycle will be held until either the sub-interval changes or additional MF\_Start\_Time and MF\_Stop\_Times are reported for the current sub-interval.

Constraints None.

## Functional Breakdown

If the Full\_PCD\_Cycle.Sub\_Intv\_Id is not the same as the MJF\_Time\_And\_ Position.Sub\_Intv\_Id then the MJF\_Time\_And\_Position data store is initialized to reflect the different sub-interval.   
Store the Full\_PCD\_Cycle.Sub\_Intv\_Id into the MJF\_Time\_And\_Position. Sub\_Intv\_Id.   
For each PCD\_Major\_Frame in the Full\_PCD\_Cycle do the following:   
Extract the Ephemeris from the PCD\_Major\_Frame.   
Extract the Attitude from each PCD\_Major\_Frame.   
Extract the Cal\_Door\_Activity\_Status from PCD\_Major\_Frame 3.   
Use the second and third bits of word 72 to determine the status of the calibration door and store as Cal\_Info.

Cal\_Door\_Activity\_Status.

Extract the spacecraft time from PCD\_Major\_Frame 1.PCD\_Minor\_Frame 96-102.Word 72.

Interpolate any missing attitude or ephemeris points using data points and time from a previous PCD\_Major\_Frame within the Sub\_Intv.

Use the Major\_Frame\_Time that is closest to the PCD spacecraft time as the time stamp for the first PCD\_Major\_Frame of the Full\_PCD\_Cycle.

Compute the Major\_Frame\_Time for the remaining PCD\_Major\_Frame of the Full\_PCD\_Cycle by incrementing the Major\_Frame\_Time by a predefined time length, insuring that the computed time does falls within the Sub\_Intv.MF\_Start\_Time and the Sub\_Intv. MF\_Stop\_Time.

Assign the attitude points to MJF\_Time\_And\_Position.Attitude.

Assign the ephemeris data points to MJF\_Time\_And\_Position.Ephemeris.

Assign the Major\_Frame\_Time to MJF\_Time\_And\_Position. Major\_Frame\_Time.

Assign the Cal\_Info.Cal\_Door\_Activity\_Status to MJF\_Time\_And\_Position. Cal\_Door\_Activity\_Status.

NAME: 4.4.2;14

TITLE: Compute Latitude And Longitude

INPUT/OUTPUT: Lat\_And\_Long : data\_out MJF\_Time\_And\_Position : data\_in Valid\_Scene\_Parms : data\_in

BODY:   
Description of Process Compute Latitude and Longitude computes the latitude and longitude for each PCD Major Frame time and position.

## Assumptions

Preconditions The transformation parameters must exist in the Valid\_Scene\_Parms.

Postconditions None.   
Constraints: None.

## Functional Breakdown

Place the MJF\_Time\_And\_Position.Sub\_Intv\_Id into Lat\_And\_Long.Sub\_Intv\_Id. For each MJF\_Time\_And\_Position associated with the MJF\_Time\_And\_Position. Sub\_Intv\_Id,

Compute the Lat\_And\_Long.Latitude using the MJF\_Time\_And\_Position. Time,MJF\_Time\_And\_Position.Position, Valid\_Scene\_Parms.ETM\_ Plus\_To\_Body\_Trans, Valid\_Scene\_Parms.Semi\_Major\_Axis, Valid\_Scene\_Parms.Semi\_Minor\_Axis and Valid\_Scene\_Parms. ETM\_Plus\_LOS as input to the Latitude and Longitude Algorithm located in Appendix C.

Compute the Lat\_And\_Long.Longitude using the MJF\_Time\_And\_Position. Time, MJF\_Time\_And\_Position.Position, Valid\_Scene\_Parms. ETM\_Plus\_To\_Body\_Trans, Valid\_Scene\_Parms.Semi\_Major\_Axis, Valid\_Scene\_Parms.Semi\_Minor\_Axis, Valid\_Scene\_Parms. ETM\_Plus\_LOS\_x, Valid\_Scene\_Parms.ETM\_Plus\_LOS\_y, and ETM\_Plus\_LOS\_z, as input to the Latitude and Longitude Algorithm located in Appendix C.

Assign the MJF\_Time\_And\_Position.Cal\_Door\_Activity\_Status to the Lat\_And\_Long.Cal\_Door\_Activity\_Status.   
Output Lat\_And\_Long.

## Reusability

The algorithm for the subroutine, JGHAX, will be re-used. JGHAX is used to compute the Greenwich Hour Angle (GHA) which is needed to compute the longitude.

NAME: 4.4.3

TITLE: Determine WRS Scene Coordinates

## INPUT/OUTPUT:

Previous\_Lat\_And\_Long : data\_inout PCD\_Scene\_Count : data\_inout Nominal\_Scene\_Coords : data\_out Actual\_Center\_Coords : data\_out Valid\_WRS\_Parms : data\_in Lat\_And\_Long : data\_in Major\_Frame\_Time : data\_in MF\_Start\_Time : data\_in MF\_Stop\_Time : data\_in

## BODY:

Description of Process Determine Scene Coordinates uses the actual latitudes and longitudes to retrieve the closest related latitude, longitude, WRS Row, and WRS Path from the WRS Table.

## Assumptions

Preconditions None.

## Postconditions Postconditions

If the current Lat\_And\_Long.Major\_Frame\_Time is greater than the corresponding Sub\_Intv.MF\_Stop\_Time then the current Lat\_ And\_Long will be held until either the sub-interval changes or additional MF\_Start\_Time and MF\_Stop\_Times are reported for the current subinterval.

Constraints None.

## Functional Breakdown

If the Lat\_And\_Long.Sub\_Intv\_Id has changed from the Previous\_Lat\_And\_ Long.Sub\_Intv\_Id then initialize the PCD\_Scene\_Count and the Previous\_Lat\_And\_Long data store.

Use the Lat\_And\_Long.Latitude and the Lat\_And\_Long.Longitude to locate the closest related scene center lat and long in the Valid\_WRS\_Parms.

If a Lat\_And\_Long.Latitude and Lat\_And\_Long.Longitude indicate that a WRS scene center has not been crossed then store the values as Previous\_Lat\_And\_Long.Latitude and Previous\_Lat\_And\_Long.Longitude.

If a Lat\_And\_Long.Latitude and Lat\_And\_Long.Longitude indicate that a WRS scene center has been crossed then retrieve the Previous\_ Lat\_And\_Long.Lat\_And\_Long.Latitude and Previous\_Lat\_And\_Long. Lat\_And\_Long.Longitude to confirm that a WRS scene center has been crossed.

Maintain a count of the number of scenes identified for each Lat\_And\_Long.Sub\_Intv\_Id as PCD\_Scene\_Count.

Use the Lat\_And\_Long values and the Previous\_Lat\_And\_Long values to calculate the Actual\_Center\_Coords.Latitude and the Actual\_Center\_Coords.Longitude by interpolation.

Store the Path and the Row of the scene center that has been crossed as the Nominal\_Scene\_Coords.WRS\_Path\_Nominal, and the Nominal\_Scene\_Coords.WRS\_Row\_Nominal.

Correlate the Lat\_And\_Long.Major\_Frame\_Time to the closest Major\_Frame\_Time within the Sub\_Intv.MF\_Start\_Time and Sub\_Intv.MF\_Stop\_Time identified by the Lat\_And\_Long.Sub\_ Intv\_Id.

Determine the sequence of the closest Major\_ Frame within the Sub\_Intv and store the value as Nominal\_Scene\_Coords.Scene\_Center\_ Scan\_Num.

Store the Lat\_And\_Long.Sub\_Intv\_Id as Actual\_Center\_Coords.Sub\_Intv\_Id.

Store the Lat\_And\_Long.Major\_Frame\_Time as Actual\_Center\_Coords.Scene\_Center\_Time.

Store the Lat\_And\_Long.Major\_Frame\_Time as Nominal\_Scene\_Coords.Scene\_Center\_Time.

Store the PCD\_Scene\_Count as

Nominal\_Scene\_Coords.PCD\_Scene\_Count

Use PCD\_Scene\_Count to store a unique scene number to Nominal\_Scene\_Coords.Sub\_Intv\_Scene\_Num.

Store the Lat\_And\_Long.Sub\_Intv\_Id as

Store the Lat\_And\_Long.Cal\_Door\_Activity\_Status as Nominal\_Scene\_Coords.Cal\_Door\_Activity\_Status.

NAME: 4.4.4;5

TITLE: Compute Horizontal Display Shift

INPUT/OUTPUT: Horizontal\_Display\_Shift : data\_out Nominal\_Scene\_Coords : data\_in Actual\_Center\_Coords : data\_in

## BODY:

Description of Process Compute Horizontal Shift Display computes the difference between the actual scene center location and the nominal scene center location.

Assumptions Preconditions None.

Postconditions None.

Constraints None.

Functional Breakdown Calculate the difference in distance between the Nominal Scene Center position and the Actual Scene Center position in meters. Output the calculated Horizontal\_Display\_Shift.

Reusability None.

NAME: 4.4.5;4

TITLE: Calculate Sun Position

INPUT/OUTPUT: Actual\_Center\_Coords : data\_in Sun\_Elevation : data\_out Sun\_Azimuth : data\_out

## BODY:

Description of Process Calculate Sun Position calculates the sun elevation and the sun azimuth for each WRS scene.

Assumptions Preconditions None.

Postconditions None.

Constraints None.

## Functional Breakdown

Use the time from the Actual\_Center\_Coords.Scene\_Center\_Time to calculate the sun vector.   
Compute the Sun\_Elevation using Actual\_Center\_Coords.Scene\_Center\_Time, Actual\_Center\_Coords.Latitude, Actual\_Center\_Coords.Longitude, and the sun vector as input to the Sun Elevation Algorithm located in Appendix C.   
Compute the Sun\_Azimuth using Actual\_Center\_Coords.Scene\_Center\_Time, Actual\_Center\_Coords.Latitude, Actual\_Center\_Coords.Longitude, and the sun vector as input to the Sun Azimuth Algorithm located in Appendix C.

## Reusability

The algorithm for the subroutine, JGHAX, will be re-used. JGHAX is used to compute the Greenwich Hour Angle (GHA) which is needed to compute the Sun\_Azimuth and the Sun\_Elevation.

NAME: 4.4.6;13

TITLE: Report Scene Info

INPUT/OUTPUT:   
Scene\_Parms : data\_out   
Scene\_Info : data\_out   
Horizontal\_Display\_Shift : data\_in   
Nominal\_Scene\_Coords : data\_in   
Sun\_Elevation : data\_in   
Sun\_Azimuth : data\_in

## BODY:

Description of Process Report Scene Info formats and reports the Scene Id for use by the Image Data Processing Subsystem (IDPS) and the Scene Parms to be included in the PCD Accounting file.

Assumptions Preconditions None.

Postconditions None.

Constraints None.

## Functional Breakdown

Extract the Nominal\_Scene\_Coords.Sub\_Intv\_Id to obtain the associated subinterval.   
Extract the Nominal\_Scene\_Coords.PCD\_Scene\_Count to determine the number of scenes identified.   
Format Nominal\_Scene\_Coords.Sub\_Intv\_Id, Nominal\_Scene\_Coords.PCD\_Scene\_Count, Nominal\_Scene\_Coords.WRS\_Path\_Nominal, Nominal\_Scene\_Coords.WRS\_Row\_Nominal, Nominal\_Scene\_Coords.Scene\_Center\_Time, Nominal\_Scene\_Coords.Scene\_Center\_Scan\_Num, Nominal\_Scene\_Coords.Sub\_Intv\_Scene\_Num, Nominal\_Scene\_Center.Cal\_Door\_Activity\_Status, Sun\_Azimuth, Sun\_Elevation, and Horizontal\_Display\_Shift as Scene\_Parms.   
Store Scene\_Parms into PCD\_Acct identified by Nominal\_Scene\_Coords. Sub\_Intv\_Id   
Store Nominal\_Scene\_Coords.PCD\_Scene\_Count as Scene\_Info.PCD\_Scene\_ Count.   
Format Nominal\_Scene\_Coords.WRS\_Path\_Nominal, Nominal\_Scene\_Coords.WRS\_Row\_Nominal, Sun\_Elevation, and

Nominal\_Scene\_Coords.Scene\_Center\_Time as Scene\_Info.Scene\_Id. Output the Scene\_Info.

NAME: 4.5;5

TITLE: Extract Major Frame Info

INPUT/OUTPUT: Drift\_Time : data\_out Sub\_Intv\_Id : data\_in Full\_PCD\_Cycle : data\_in

BODY:   
Description of Process Extract Major Frame Info extracts the drift rate from each Full\_PCD\_Cycle.

Assumptions Preconditions None.

Post conditions None.

Constraints Each Full\_PCD\_Cycle must contain the complete Drift\_Rate.

## Functional Breakdown

Extract the Drift\_Time from the first PCD Major Frame of each Full\_PCD\_Cycle.   
Assign the current Full\_PCD\_Cycle.Sub\_Intv\_Id to Drift\_Time. Sub\_Intv\_Id.   
Assign the drift rate to Drift\_Time.Drift\_Rate.   
Output the Drift\_Time.

Reusability None.

NAME: 4.6;14

TITLE: Create PCD File

INPUT/OUTPUT: Current\_Orbit : data\_inout PCD\_File\_Info : data\_out Qualified\_PCD\_Cycle : data\_out MF\_Start\_Time : data\_in Major\_Frame\_Time : data\_in Time\_Per\_Orbit : data\_in Full\_PCD\_Cycle : data\_in MF\_Stop\_Time : data\_in LPS\_Configuration : data\_in

## BODY:

Description of Process Create PCD File creates the PCD\_File using Full\_PCD\_Cycle and calculates the PCD\_File related statistics on a Sub\_Intv basis.

## Assumptions

Preconditions The Valid\_Scene\_Parms.Mission\_Start\_Time is stored as Current\_Orbit.Orbit\_Time at the beginning of the LPS mission. Zero is stored as the Current\_Orbit.Orbit\_Num at the beginning of the LPS mission. The PCD\_File\_Name consists of the LPS\_Configuration. File\_Version\_Number, Sub\_Intv.MF\_Start\_Time, and the PCD\_File\_Type.

Post conditions None.

Constraints None.

Functional Breakdown If a PCD\_File is open then the Full\_PCD\_Cycle is written to the current PCD\_File. If a PCD\_File is not open then a new PCD\_File is opened, assigned a PCD\_File\_Name, and the current Full\_PCD\_Cycle will be written to the new PCD\_File. The PCD\_File\_Name of the new PCD\_File will be stored. If the Full\_PCD\_Cycle has a null value which indicates that a contact period has ended, then Format and store PCD\_File\_Info.PCD\_File\_Name, PCD\_File\_Info.Num\_PCD\_MJF, and PCD\_File\_Info.First\_PCD\_MJF\_Time Close the current PCD\_File. Extract the spacecraft time from Full\_PCD\_Cycle.PCD\_Major\_Frame 0. If the Full\_PCD\_Cycle is the first Full\_PCD\_Cycle for the current Full\_PCD\_Cycle.Sub\_Intv\_Id then store the spacecraft time as

the PCD\_File\_Info.First\_PCD\_MJF\_Time.

Compare the PCD\_File\_Info.First\_PCD\_MJF\_Time to the Current\_Orbit.Orbit\_Time to determine the current orbit.

If the PCD\_File\_Info.First\_PCD\_MJF\_Time is <= the Current\_ Orbit.Orbit\_Time then store the Current\_Orbit. Orbit\_Num as PCD\_File\_Info.Orbit\_Num.

If the PCD\_File\_Info.First\_PCD\_MJF\_Time is > the Current\_ Orbit.Orbit\_Time then increment the Current\_ Orbit.Orbit\_Num by one, increment the Current\_ Orbit.Orbit\_Time by the Valid\_Scene\_Parms.Time\_Per\_ Orbit and store the Current\_Orbit.Orbit\_Num as PCD\_File\_Info.Orbit\_Num.

Compare the spacecraft time to the current Sub\_Intv.MF\_Start\_Time and Sub\_Intv.MF\_Stop\_Time time range, identified by Full\_PCD\_Cycle.Sub\_Intv\_Id, to determine if the Full\_PCD\_Cycle is a Qualified\_PCD\_Cycle for the current Sub\_Intv.

If the Full\_PCD\_Cycle is a Qualified\_PCD\_Cycle for the current Sub\_Intv, then Store the Qualified\_PCD\_Cycle in PCD\_File. Calculate the PCD\_File\_Info.Num\_PCD\_MJF.

If the Full\_PCD\_Cycle is not a Qualified\_PCD\_Cycle for the current Sub\_Intv then format and store PCD\_File\_Info.PCD\_File\_Name, PCD\_File\_Info.Num\_PCD\_MJF, PCD\_File\_Info.First\_PCD\_ MJF\_Time, and PCD\_File\_Info.Orbit\_Num as PCD\_File\_Info. Close the current PCD\_File.

Place the contents of PCD\_File\_Info into the PCD\_Acct store identified by Full\_PCD\_Cycle.Sub\_Intv\_Id.

Reusability

None.

## 4.7.2 Performance Requirements

The following list summarizes the performance requirements allocated to the PCDS:

4.7.2.1 The PCDS software on each LPS string shall provide the capability to process the equivalent of any combination of the format 1 and format 2 portions of 125 Landsat 7 ETM+ scenes of wideband data per day (approximately 25-30 GB per day).

4.7.2.2 The PCDS software on each LPS string shall process unpacked PCD data at a minimum rate of not less than 3.2 kilobits per second (Kbps) (based on a minimum raw wideband throughput of 7.5 Mbps)

4.7.2.3 The PCDS software on each LPS string shall provide the capability to execute concurrently with all other LPS subsystems.

4.7.2.3.1 The PCDS software shall begin to process received raw wideband data immediately upon receipt of required inputs.

4.7.2.3.2 The PCDS software shall output a scene center identification, a sun azimuth at scene center value, and a sun elevation at scene center value within 240 seconds of the time of receiving all required inputs.

4.7.2.4 The PCDS software on each LPS string shall provide the capability to reprocess a maximum of 10% of a string's daily input volume of wideband data (approximately 12.5 scenes or 2.5-3 GB per day).

4.7.2.5 The PCDS software on each LPS string shall provide the capability to process unpacked PCD data at a daily average aggregate rate of 12.7 Kbps per second (Includes 10% of overhead due to reprocessing).

4.7.2.6 The PCDS software on each LPS string shall maintain data processing throughput performance for all Landsat 7 raw wideband data received with a BER of one bit error in 105 bits, without loss of level zero processed data and without retransmission. [

4.7.2.7 The PCDS software on each LPS string shall output any periodic processing status information that it generates with a maximum latency of 30 seconds between outputs.

## 4.8 Image Data Processing Subsystem (IDPS)

This subsystem is responsible for producing band and browse image files, generating cloud coverage assessment scores, and validating certain user-defined parameters that are necessary for the subsystem.

## 4.8.1 Functional Requirements

The following list summarizes the functional requirements allocated to the IDPS:

•validate and store the processing parameters received from MACS.

generate monochrome or multiband browse data for each ETM+ image on a subinterval basis.

•generate band file for each band received on a subinterval basis.

•perform Automatic Cloud Cover Assessment (ACCA) for WRS scenes using predefined comparison values on scene quadrant and full scene basis.

## 4.8.1.1 Major Functions

The IDPS subsystem, in its Band File Generation process, takes aligned band data from MFPS, separates it by subinterval and band, and produces band files. In the Browse File Generation process, the aligned band data is separated by subinterval and then reduced by subsampling and wavelet algorithms to produce monochrome and multiband browse files. In the ACCA process, the aligned band data is separated by scenes, and then an ACCA algorithm is used on the data to produce ACCA scores. Certain parameters used in the above processes are also validated before their use in the Validate Band Parameters process. Finally, accounting information is produced for metadata generation and the band and browse files are made available to the LDTS.

The major functions of IDPS are depicted in the following data flow diagrams.

## 4.8.1.2 Interface Requirements

The following two tables summarize the interface requirements for the IDPS:

Table 4.9 IDPS Interface Requirements - INPUT
<table><tr><td rowspan=1 colspan=1>Input Item Name</td><td rowspan=1 colspan=1>Source</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>Aligned_Bands</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>Bands aligned along band anddetector</td></tr><tr><td rowspan=1 colspan=1>Status_Info</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>Status information from the VCDU</td></tr><tr><td rowspan=1 colspan=1>Sub_Intv</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>Subinterval id, start time andstop time</td></tr><tr><td rowspan=1 colspan=1>Drift_Time</td><td rowspan=1 colspan=1>PCDS</td><td rowspan=1 colspan=1>Difference between spacecrafttime and actual time</td></tr><tr><td rowspan=1 colspan=1>Scene_Info</td><td rowspan=1 colspan=1>PCDS</td><td rowspan=1 colspan=1>Parameters used to calculate thescene identification</td></tr><tr><td rowspan=1 colspan=1>File_Version_Number</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>File identifier for reprocessing</td></tr><tr><td rowspan=1 colspan=1>IDP_Band_Parms</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Operator-defined       parametersspecifying whichbandstoprocess, whether to use band 6for format 1 or 2, reduction ratiosfor Browse and ACCA, and theACCA method used</td></tr></table>

Table 4.10 IDPS Interface Requirements - OUTPUT
<table><tr><td rowspan=1 colspan=1>Output Item Name</td><td rowspan=1 colspan=1>Destination</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>Browse_File</td><td rowspan=1 colspan=1>LDTS</td><td rowspan=1 colspan=1>Monochrome and/or Multibandreduced image files.</td></tr><tr><td rowspan=1 colspan=1>Band_File</td><td rowspan=1 colspan=1>LDTS</td><td rowspan=1 colspan=1>3 or 6 separate band files forbands 6, 7 &amp; Pan or bands 1-6</td></tr><tr><td rowspan=1 colspan=1>IDP_Acct</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Accounting information fromBrowse, Band and ACCA</td></tr><tr><td rowspan=1 colspan=1>IDP_Setup_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Status returned from validatingIDP_Band_Parms</td></tr><tr><td rowspan=1 colspan=1>IDP_ACCA_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Status returned from ACCA</td></tr></table>

## 4.8.1.3 Detailed Functional Requirements

This section contains the process specifications for the lowest level processes in the IDPS data flow diagrams.

NAME: 5.1;10

TITLE: Validate IDP Parameters

INPUT/OUTPUT: IDP\_Setup\_Status : data\_out Valid\_Band\_Parms : data\_out IDP\_Band\_Parms : data\_in

## BODY:

## Description of Process

This function validates one or more of the following values of IDP\_Band\_Parms: the four band parameters that indicate which bands to process for Browse (IDP\_Band\_Parms.Mono, IDP\_Band\_Parms.Multi1, IDP\_Band\_Parms.Multi2, IDP\_Band\_Parms.Multi3), and reduction ratios for performing the subsampling, wavelet and ACCA algorithms (IDP\_Band\_Parms.Subs, IDP\_Band\_Parms.Wave and IDP\_Band\_Parms.CCA\_Ratio). If valid, these values are placed in the datastore Valid\_Band\_Parms along with the identifier of the ACCA algorithm used (IDP\_Band\_Parms.CCA\_Method) which does not need to be validated.

## Assumptions

## Preconditions

One or more of the following values of IDP\_Band\_Parms have been entered by an operator and passed to the task: Four band parameters (IDP\_Band\_Parms.Mono, IDP\_Band\_Parms.Multi1, IDP\_Band\_Parms.Multi2, IDP\_Band\_Parms.Multi3),both a subsampling and wavelet reduction ratio (IDP\_Band\_Parms.Subs and IDP\_Band\_Parms.Wave), and two ACCA parameters (IDP\_Band\_Parms.CCA\_Method and IDP\_Band\_Parms.CCA\_Ratio). There are valid default values for each of the above parameters in the datastore Valid\_Band\_Parms.

## Postconditions

The following valid values exist in the datastore Valid\_Band\_Parms: Four band parameters (Valid\_Band\_Parms. Mono, Valid\_Band\_Parms.Multi1, Valid\_Band\_Parms.Multi2, Valid\_Band\_Parms.Multi3),both a subsampling and wavelet reduction ratio (Valid\_Band\_Parms.Subs and Valid\_Band\_Parms.Wave) and two ACCA parameters (Valid\_Band\_Parms.CCA\_Method and Valid\_Band\_Parms. CCA\_Ratio).

## Constraints

Any changes to the band parameters will take effect at the start of the next contact period, which is identified in Sub\_Intv.Contact\_Id.

## Functional Breakdown

Get any values for IDP\_Band\_Parms that are passed to this subsystem and validate their values. Following are the valid values for each:

Mono

1-7 or Pan

Multi1 1-7 or Pan   
Multi2 1-7 or Pan   
Multi3 1-7 or Pan   
Subs 2-16   
Wave 2-16.   
CCA\_Ratio 4,8,16,32,48   
CCA\_Method arbitrary string - no validation needed

Send status (IDP\_Status.IDP\_Setup\_Status) back to MACS indicating the success or failure of the validations so that appropriate messages may be logged and displayed.

The following assignments are made only if a new value is passed to the subsystem and if that value is valid:

Valid\_Band\_Parms.Mono = IDP\_Band\_Parms.Mono

Valid\_Band\_Parms.Multi1 = IDP\_Band\_Parms.Multi1

Valid\_Band\_Parms.Multi2 = IDP\_Band\_Parms.Multi2

Valid\_Band\_Parms.Multi3 = IDP\_Band\_Parms.Multi3

Valid\_Band\_Parms.Subs = IDP\_Band\_Parms.Subs

Valid\_Band\_Parms\_Wave = IDP\_Band\_Parms.Wave

Valid\_Band\_Parms.CCA\_Method = IDP\_Band\_Parms.CCA\_Method

Valid\_Band\_Parms.CCA\_Ratio = IDP\_Band\_Parms.CCA\_Ratio

NAME: 5.2.1;14

TITLE: Reduce Image by Subsamples

## INPUT/OUTPUT:

Browse\_Store : data\_inout Overlay\_Subs : data\_out Mono\_Band\_Subs : data\_out Multi\_Band\_Subs : data\_out Valid\_Band\_Parms : data\_in Aligned\_Bands : data\_in Sub\_Intv : data\_in Status\_Info : data\_in Scene\_Info : data\_in

## BODY:

## Description of Process

This function reduces an image by saving only the pixels in every Nth row and Nth column. The process is called subsampling by N where N is a user-defined parameter.

## Assumptions

## Preconditions

There are four valid band parameters indicating which bands to process (Valid\_Band\_Parms.Mono, Valid\_Band\_Parms.Multi1, Valid\_Band\_Parms.Multi2, Valid\_Band\_Parms.Multi3),and subsampling and wavelet reduction ratios (Valid\_Band\_Parms.Subs and Valid\_Band\_Parms.Wave) stored in Valid\_Band\_Parms. Valid band parameters are 1-6. Aligned band data (Aligned\_ Bands) has been passed to the subsystem and subinterval definitions are available in the datastore Sub\_Intv. The Status\_Info.Fmt\_Id, which identifies the scene data as either 1 or 2, has been passed to the subsystem.

## Post conditions

Multi\_Band\_Subs and/or Mono\_Band\_Subs have been created by subsampling. Mono\_Band\_Subs contains monochrome browse data from one predetermined band. Multi\_Band\_Subs, if it exists, contains multiband browse data from three predetermined bands. Multi\_Band\_Subs will only be created if Status\_Info.Fmt\_Id is 1.

## Constraints

None.

## Functional Breakdown

Get subinterval start and stop times (Sub\_Intv.MF\_Start\_Time and Sub\_Intv.MF\_Stop\_Time), and Sub\_Intv.Contact\_Id from the Sub\_Intv datastore identified by Aligned\_Bands. Sub\_Intv\_Id.

Get Valid\_Band\_Parms.Subs from datastore Valid\_Band\_Parms.

For each new contact period (when Sub\_Intv.Contact\_Id changes), get the following parameters from datastore Val\_Band\_Parms:

Valid\_Band\_Parms.Mono Valid\_Band\_Parms.Multi1 Valid\_Band\_Parms.Multi2 Valid\_Band\_Parms.Multi3

Place Aligned\_Bands data into datastore Browse\_Store until the data for one subinterval has accumulated (when Aligned\_Bands.Sub\_Intv\_Id changes).   
Then get from Browse\_Store the Aligned\_Bands data for one subinterval.

If Status\_Info.Format\_Id is 1, then Save only the Aligned\_Bands data where Aligned\_Bands.Band\_Num matches one of the four band parameters in Valid\_Band\_Parms. If one of the four band parameters in Valid\_Band\_Parms is 6 and if Valid\_Band\_Parms.Fmt is 1, then Retain Band 6 for format 1 scene data only.

Subsample the Aligned\_Bands data by saving the pixel from every Nth row and Nth column where N is Valid\_Band\_Parms.Subs.

Do this where Aligned\_Bands.Band\_Num matches Valid\_Band\_Parms.Mono to produce reduced monochrome image data contained in Mono\_Band\_Subs.

If Status\_Info.Format\_Id is 1, do this where Aligned\_Bands.Band\_Num matches Valid\_Band\_Parms.Multi1, Valid\_Band\_Parms.Multi2, and Valid\_Band\_Parms.Multi3 to produce reduced multiband image data contained in Multi\_Band\_Subs.

For each subsampled pixel which represents data that includes a scene center (identified by Scene\_Info.Scene\_Id), place the Scene\_Info.Scene\_Id and the pixel location in Overlay\_Subs. Overlay\_Marks.

Append to Overlay\_Subs, Mono\_Band\_Subs, and Multi\_Band\_Subs the Aligned\_Bands.Sub\_Intv\_Id, the Sub\_Intv.MF\_Start\_Time and Sub\_Intv.MF\_Stop\_Time identified by Aligned\_Bands.Sub\_Intv\_Id, and the browse image reduction ratios (Valid\_Band\_Parms.Subs and Valid\_Band\_Parms.Wave).

Output the Mono\_Band\_Subs, Multi\_Band\_Subs, and Overlay\_Subs.

## Reusability

The prototype written by Lizz Pena and described in a paper written in Summer, 1994, ("Landsat Browse Generation Using Wavelets for Image Reduction") may be reused.

The algorithm to separate aligned band data by subinterval may be reused for Band File Generation and ACCA.

NAME: 5.2.2;14

TITLE: Reduce Image by Wavelets

INPUT/OUTPUT:   
Browse\_File : data\_out   
Browse\_Acct : data\_out   
Multi\_Band\_Subs : data\_in   
Mono\_Band\_Subs : data\_in   
Wave : data\_in   
Overlay\_Subs : data\_in   
File\_Version\_Number : data\_in   
MF\_Start\_Time : data\_in

## BODY:

Description of Process This function reduces an image by replacing an N X N grid of pixels with one pixel where the intensity of that one pixel is the average intensity of the entire grid of pixels. N is a user-defined parameter.

## Assumptions

Preconditions Multi\_Band\_Subs and/or Mono\_Band\_Subs have been produced by subsampling and have been passed to the task. There is a wavelet reduction ratio, Valid\_Band\_Parms.Wave, in the Valid\_Band\_Parms datastore.

## Post conditions

Multi\_Band\_Wave and/or Mono\_Band\_Wave have been created using the wavelet algorithm.   
Mono\_Band\_Wave contains monochrome browse data from one predetermined band.   
Multi\_Band\_Wave, if it exists, contains multiband browse data from three predetermined bands.   
Browse\_Acct has been passed to the IDP\_Acct datastore.

## Constraints

If Multi\_Band\_Subs has not been passed to this task, Multi\_Band\_Wave will not be generated. Browse file will not be created for format 2 data.

## Functional Breakdown

Get wavelet reduction ratio Valid\_Band\_Parms.Wave from Valid\_Band\_Parms datastore.

Reduce Mono\_Band\_Subs by replacing each N X N grid of pixels with one pixel where the intensity of that one pixel is the average intensity of the entire grid of pixels. N is Valid\_Band\_Parms.Wave. The result is Mono\_Band\_Wave.   
For each wavelet reduced pixel which contains a scene center   
(identified in Overlay\_Subs.Overlay\_Marks),   
Copy the Overlay\_Subs.Overlay\_Marks.Scene\_Id to Overlay\_Wave.Overlay\_Marks.Scene\_Id and insert the pixel location into Overlay\_Wave.Overlay\_Mark. Pixel\_Index.

Place Overlay\_Wave and Mono\_Band\_Wave into Browse\_File.

If Multi\_Band\_Subs has been passed to this task, then Replace each N X N grid of pixels with one pixel where the intensity of that one pixel is the average intensity of the entire grid of pixels. N is Valid\_Band\_Parms.Wave. The result is Multi\_Band\_Wave. Place Multi\_Band\_Wave into Browse\_File.

Create the Mono\_Browse\_File\_Name using LPS\_Configuration. File\_Version\_Number and Sub\_Intv.MF\_Start\_Time identified by the Mono\_Band\_Subs.Sub\_Intv\_Id.

If Multi\_Band\_Wave exists, Create the Multi\_Browse\_File\_Name using LPS\_Configuration. File\_Version\_Number and Sub\_Intv.MF\_Start\_Time identified by the Mono\_Band\_Subs.Sub\_Intv\_Id.

Place the Mono\_Band\_Subs.Sub\_Intv\_Id into Browse\_Acct.Sub\_Intv\_Id.

Place Multi\_Browse\_File\_Name and/or Mono\_Browse\_File\_Name in Browse\_Acct.Browse\_File\_Names.

Place Browse\_Acct into IDP\_Acct identified by Browse\_Acct.Sub\_Intv\_Id.

## Reusability

The prototype written by Lizz Pena during the Summer, 1994, ("Landsat Browse Generation Using Wavelets for Image Reduction") may be reused.

NAME: 5.3;10

TITLE: Generate Band File

## INPUT/OUTPUT:

Band\_Store : data\_out Band\_File : data\_out Band\_Acct : data\_out Aligned\_Bands : data\_in Drift\_Time : data\_in Status\_Info : data\_in Band\_Store : data\_in MF\_Start\_Time : data\_in File\_Version\_Number : data\_in

## BODY:

Description of Process This function generates one file for each band and appends the Drift\_Time and Status\_Info to each file. These files are produced on a subinterval basis.

## Assumptions

Preconditions None.

Postconditions Three or six band files have been generated and the Drift\_ Time and Status\_Info have been appended to each band file. Band\_Acct has been passed to the IDP\_Acct datastore.

Constraints None.

Functional Breakdown Place Aligned\_Bands data into datastore Band\_Store until the data for one subinterval has accumulated (when Aligned\_Bands.Sub\_Intv\_Id changes). Get from Band\_Store the Aligned\_Bands for the current subinterval.

If Status\_Info.Format\_Id is 1, then Place the Aligned\_Bands data for bands 1-6 in six separate files, one file for each band.   
If Status\_Info.Format\_Id is 2, then Place the Aligned\_Bands data for bands 6, 7, and Pan in three separate files, one for each band.

Append to each band file the Status\_Info and Drift\_Time. The resulting files are App\_Data\_Band1, App\_Data\_Band2, ..., App\_Data\_Band7, App\_Data\_Pan. Place these band files into Band\_File.

Place Aligned\_Bands.Sub\_Intv\_Id into Band\_Acct.Sub\_Intv\_Id If Status\_Info.Format\_Id is 1,

Place band numbers 1-6 into Band\_Acct.Bands\_Present.

Create the Band\_File\_Names for bands 1-6 using

LPS\_Configuration.File\_Version\_Number and Sub\_Intv.

MF\_Start\_Time identified by Aligned\_Bands.Sub\_Intv\_Id.

If Status\_Info.Format\_Id is 2,

Place band numbers 6, 7 and Pan in Bands\_Present. Create the Band\_File\_Names for bands 6, 7 and Pan using LPS\_Configuration.File\_Version\_Number and Sub\_Intv. MF\_Start\_Time identified by Aligned\_Bands.Sub\_Intv\_Id.

Place the Band\_File\_Names into Band\_Acct.Band\_File\_Names.

Place Status\_Info.Band\_Gains into Band\_Acct.Band\_Gains.

Place Status\_Info.Gain\_Change\_Flag into Band\_Acct.Gain\_Change\_Flag.

Place the Band\_Acct into the IDP\_Acct store identified by Band\_Acct. Sub\_Intv\_Id.

## Reusability

The algorithm to separate aligned band data by subinterval may be reused for Browse File Generation and ACCA.

NAME: 5.4.1;9

TITLE: Collect Scene Data

INPUT/OUTPUT: PCD\_Scene\_Count : data\_out Aligned\_Bands : data\_out IDP\_ACCA\_Status : data\_out Scene\_Metadata : data\_out Scene\_Data : data\_out Status\_Info : data\_in Aligned\_Bands : data\_in Scene\_Info : data\_in Scene\_Data : data\_in

## BODY:

Description of Process This function collects the scene data (identified by the Scene\_Info.Scene\_Id) from the Aligned\_Bands stream. Cloud Cover Assessment only works with format 1 data.

## Assumptions

Preconditions Scene\_Id will be a valid identifier of a scene that is contained in the current Aligned\_Bands.

Postconditions Scene\_Data will contain the entire data for the identified scene. The Scene\_Metadata will contain the data to uniquely identify the data.

Constraints The Aligned\_Bands data stream must contain the correct data that may be found using the Scene\_Info. Scene\_Id. Cloud Cover Assessment is only performed on Format 1 data. A full scene's worth of data must be available to be collected.

## Functional Breakdown

Place Scene\_Info.PCD\_Scene\_Count into the IDP\_Acct. PCD\_Scene\_Count identified by Aligned\_Bands.Sub\_Intv\_Id.

For each identified scene (PCD\_Scene\_Count) in Scene\_Info do the following:

If Status\_Info.Format\_Id is 1, i.e. bands 1-6 exist, do Use Scene\_Info.Scene\_Id to find the location of the start of the scene. Scene\_Info.Scene\_Id identifies the scene center.

Use an appropriate delta to find the scene start time.

Read Aligned\_Bands until scene start time is found.

Place Aligned\_Bands into Scene\_Data\_Store until the end of the scene.

If the full scene is not in the subinterval, then Create a IDP\_ACCA\_Status message indicating that no CCA can be performed because there is not a full scene's worth of data.

Otherwise,

Pull the Scene\_Data from the Scene\_Data\_Store for the scene and output.

Place Aligned\_Bands.Sub\_Intv\_Id and Scene\_Info.Scene\_Id into Scene\_Metadata.

Output Scene\_Metadata and Scene\_Data.

Otherwise,

Create IDP\_ACCA\_Status indicating there the data was of the incorrect format.

## Reusability

Possible reuse of scene collection algorithm.

Generating and sending status messages. Every major function (and probably most minor functions) will need to send messages to the MACS.

NAME: 5.4.2;10

TITLE: Generate Cloud Cover Assessment

INPUT/OUTPUT: ACCA\_Acct : data\_out IDP\_ACCA\_Status : data\_out Scene\_Data : data\_in CCA\_Method : data\_in Scene\_Metadata : data\_in CCA\_Ratio : data\_in

## BODY:

Description of Process The Generate Cloud Cover Assessment function determines percentage of cloud coverage on a scene quadrant and full scene basis. The function subsamples, using the Valid\_Band\_Parms.CCA\_Ratio, and the scene data from specified bands (TBD).

## Assumptions

Preconditions The Scene\_Data must contain all of the data for a scene.

Postconditions Five percentage scores have been generated and put in ACCA: one for each quadrant and an aggregate score for the scene. Status messages are sent indicating that CCA has been performed on a specific scene.

Constraints Cloud cover assessment is only given for full scenes. Fill within major frames is allowable; it just won't be used in calculating an assessment.

## Functional Breakdown

Find the start of each quadrant in Scene\_Data.

Use Scene\_Metadata.Scene\_Id.Sun\_Elevation to calculate a threshold used by the assessment algorithm.

For each quadrant in the scene Pull data values from the Scene\_Data at the sampling ratio defined by Valid\_Band\_Parms.CCA\_Ratio.

Examine data values against the cloud cover assessment thresholds or algorithm.

Compile the cloud cover percentage quadrant score and place in ACCA\_Acct.ACCA.CC\_Quadrant#\_Score.

Average the quadrant assessments for a scene score and place into ACCA\_Acct.ACCA.CCA\_Aggregate\_Score

Place Valid\_Band\_Parms.CCA\_Method into ACCA\_Acct. Place Scene\_Metadata.Sub\_Intv\_Id into ACCA\_Acct.Sub\_Intv\_Id. Place ACCA\_Acct into the IDP\_Acct store for this scene, identified by the ACCA\_Acct.Sub\_Intv\_Id.

Create a IDP\_Status.IDP\_ACCA\_Status message indicating CCA scores have been generated for the scene.

## Reusability

Possibilities for reuse include:

Generating accounting information. This function will be needed by almost every component of the LPS so there is a possibility the code could be reused.

Cloud Cover Assessment algorithm. A prototype was created for the ACCA. If the algorithm used in the prototype is the eventual assessment algorithm or if the algorithm used is from another project, much of the code is reusable. For more information on the prototype, please refer to the "Prototype White Paper", September 1994.

Generating and sending status messages. Every major function (and probably most minor functions) will need to send messages to the MACS.

## 4.8.2 Performance Requirements

The following list summarizes the performance requirements allocated to the IDPS:

4.8.1 The IDPS software on each LPS string shall provide the capability to process the equivalent of any combination of the format 1 and format 2 portions of 125 Landsat 7 ETM+ scenes of wideband data per day (approximately 25-30 GB per day).

4.8.2 The IDPS software on each LPS string shall process aligned band data at a minimum rate of not less than 7.5 Mbps (based on a minimum raw wideband throughput of 7.5 Mbps without PCD and CADU overhead).

4.8.3 The IDPS software on each LPS string shall provide the capability to execute concurrently with all other LPS subsystems.

4.8.3.1 The IDPS software on each LPS string shall begin to process received data immediately upon receipt of required inputs.

4.8.3.2 The IDPS software on each LPS string shall output scene metadata within 250 seconds of the time of receiving all required inputs.

4.8.4 The IDPS software on each LPS string shall provide the capability to reprocess a maximum of 10% of a string's daily input volume of data (approximately 12.5 scenes or 2.5-3 GB per day).

4.8.5 The IDPS software on each LPS string shall provide the capability to process received data at a daily average aggregate rate of 2.9 megabits per second (Mbps) (Includes 10% of overhead due to reprocessing).

4.8.6 The IDPS software on each LPS string shall maintain data processing throughput performance for all Landsat 7 raw data received with a BER of one bit error in 105 bits, without loss of level zero processed data and without retransmission.

4.8.7 The IDPS software on each LPS string shall output any periodic processing status information that it generates with a maximum latency of 30 seconds between outputs.

## 4.9 Management and Control Subsystem (MACS)

This subsystem is responsible for system level control and monitoring of LPS devices and processes, providing the interface between the LPS system and the operator, and generating the Metadata files on a subinterval basis.

## 4.9.1 Functional Requirements

The following list summarizes the functional requirements allocated to the MACS:

• provide an orderly system start-up and shut-down capability.

provide the capability to monitor and control LPS operation, including the display of error messages or alarms to the operator.

• generate Level 0R metadata file(s) on a subinterval basis.

provide the capability to display and/or print LPS summary or quality and accounting information upon operator request.

provide monitoring test points and indicators to verify proper operation of system capabilities and components.

• provide the capability to manually override LPS automated functions or to suspend LPS file generation.

• notify LDTS when to send the DAN to LP DAAC.

## 4.9.1.1 Major Functions

Upon receipt of operator keyed Directive, the MACS first determines which subsystem the directive belongs to and forwards the Directive to the target subsystem. If the Directive is either MACS\_Modify\_Schedule\_Drct or MACS\_Modify\_Config\_Drct, it sends the Directive to Modify Contact Schedule or Modify LPS Configuration function to modify the appropriate data store. If the Directive is MACS\_Control\_Drct, it sends it to LPS System Control function for LPS system level control.

When the RDP\_Process\_Drct is issued, the Contact\_Id is forwarded to the Generate Metadata process, which generates a metadata file for each subinterval in the contact period. Once all associated metadata files are completed, the MACS sends a notification (LDT\_Send\_DAN) with Contact\_Id to the LDTS for the readiness of file transfer to LP DAAC.

During LPS operation, the MACS monitors for system failure. It receives the processing status (RDC\_Return\_Status, RDP\_Return\_Status, MFP\_Return\_Status, PCD\_Return\_Status, IDPS\_Return\_Status, and LDTS\_Return\_Status) from the subsystems and displays it to the operator. It also displays or reports the quality and accounting information (LPS\_Acct) or summary information (Data\_Receive\_Summary, Return\_Link\_QA\_ Report, Level0R\_QA, and LDT\_Transfer\_Sum) upon operator request.

The major functions of MACS are depicted in the following data flow diagrams.

Figure 4-18   
MACS - DFD 6.0

## 4.9.1.2 Interface Requirements

The following two tables summarize the interface requirements for the MACS:

Table 4.11 MACS Interface Requirements - INPUT
<table><tr><td rowspan=1 colspan=1>Input Item Name</td><td rowspan=1 colspan=1>Source</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>Current_Time</td><td rowspan=1 colspan=1>TimeSource</td><td rowspan=1 colspan=1>System wide time source</td></tr><tr><td rowspan=1 colspan=1>Directive</td><td rowspan=1 colspan=1>Operator</td><td rowspan=1 colspan=1>Operator commands</td></tr><tr><td rowspan=1 colspan=1>RDC_Status</td><td rowspan=1 colspan=1>RDCS</td><td rowspan=1 colspan=1>Processing Status</td></tr><tr><td rowspan=1 colspan=1>RDP_Status</td><td rowspan=1 colspan=1>RDPS</td><td rowspan=1 colspan=1>Processing Status</td></tr><tr><td rowspan=1 colspan=1>MFP_Status</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>Processing Status</td></tr><tr><td rowspan=1 colspan=1>PCD_Status</td><td rowspan=1 colspan=1>PCDS</td><td rowspan=1 colspan=1>Processing Status</td></tr><tr><td rowspan=1 colspan=1>IDP_Status</td><td rowspan=1 colspan=1>IDPS</td><td rowspan=1 colspan=1>Processing Status</td></tr><tr><td rowspan=1 colspan=1>LDT_Status</td><td rowspan=1 colspan=1>LDTS</td><td rowspan=1 colspan=1>Processing Status</td></tr><tr><td rowspan=1 colspan=1>Report_RDC_Data_Capture_Sum</td><td rowspan=1 colspan=1>RDCS</td><td rowspan=1 colspan=1>Data capture summary on acontact period basis</td></tr><tr><td rowspan=1 colspan=1>Report_RDP_Return_Link_QA</td><td rowspan=1 colspan=1>RDPS</td><td rowspan=1 colspan=1>Return_Link quality andaccounting information report</td></tr><tr><td rowspan=1 colspan=1>Report_MFP_LOR_QA</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>Level_OR file quality andlaccounting      information report</td></tr><tr><td rowspan=1 colspan=1>Report_LDT_File_Xfer_Sum</td><td rowspan=1 colspan=1>LDTS</td><td rowspan=1 colspan=1>LPS file transfer summary reporton a contact period basis</td></tr><tr><td rowspan=1 colspan=1>LPS_Acct</td><td rowspan=1 colspan=1>RDCS, RDPS,MFPS, PCDS,IDPS</td><td rowspan=1 colspan=1>LPS quality and accountinginformation for metadata filecreation on a subinterval basis</td></tr><tr><td rowspan=1 colspan=1>Sub_Intv</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>Subinterval information formetadata file creation</td></tr><tr><td rowspan=1 colspan=1>Valid_WRS_Parms</td><td rowspan=1 colspan=1>PCDS</td><td rowspan=1 colspan=1>Scene path/row andlongiture/latitude information</td></tr></table>

Table 4.12 MACS Interface Requirements - OUTPUT
<table><tr><td rowspan=1 colspan=1>Output Item Name</td><td rowspan=1 colspan=1>Destination</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>RDC_Directive</td><td rowspan=1 colspan=1>RDCS</td><td rowspan=1 colspan=1>Control Directive</td></tr><tr><td rowspan=1 colspan=1>RDP_Directive</td><td rowspan=1 colspan=1>RDPS</td><td rowspan=1 colspan=1>Control Directive</td></tr><tr><td rowspan=1 colspan=1>MFP_Directive</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>Control Directive</td></tr><tr><td rowspan=1 colspan=1>PCD_Directive</td><td rowspan=1 colspan=1>PCDS</td><td rowspan=1 colspan=1>Control Directive</td></tr><tr><td rowspan=1 colspan=1>[IDP_Directive</td><td rowspan=1 colspan=1>IDPS</td><td rowspan=1 colspan=1>Control Directive</td></tr><tr><td rowspan=1 colspan=1>LDT_Directive</td><td rowspan=1 colspan=1>LDTS</td><td rowspan=1 colspan=1>Control Directive</td></tr><tr><td rowspan=1 colspan=1>Contact_Schedules</td><td rowspan=1 colspan=1>RDCS</td><td rowspan=1 colspan=1>Data receive schedule</td></tr><tr><td rowspan=1 colspan=1>LPS_Configuration</td><td rowspan=1 colspan=1>RDCS, RDPS,MFPS, LDTS</td><td rowspan=1 colspan=1>LPS setup parameters</td></tr><tr><td rowspan=1 colspan=1>LPS_Report</td><td rowspan=1 colspan=1>Operator</td><td rowspan=1 colspan=1>LPS summary report</td></tr><tr><td rowspan=1 colspan=1>LPS_Status</td><td rowspan=1 colspan=1>Operator</td><td rowspan=1 colspan=1>LPS processing status</td></tr><tr><td rowspan=1 colspan=1>Metadata_File</td><td rowspan=1 colspan=1>LDTS</td><td rowspan=1 colspan=1>Metadata file on a subintervalbasis</td></tr><tr><td rowspan=1 colspan=1>LDT_Send_DAN</td><td rowspan=1 colspan=1>LDTS</td><td rowspan=1 colspan=1>LPS files ready for transmissionnotification</td></tr></table>

## 4.9.1.3 Detailed Functional Requirements

This section contains the process specifications for the lowest level processes in the MACS data flow diagrams.

NAME: 6.1

TITLE: Process LPS Directive

INPUT/OUTPUT:   
Contact\_Id : data\_out   
MACS\_Modify\_Schedule\_Drct : data\_out   
MACS\_Modify\_Config\_Drct : data\_out   
MACS\_Directive\_Dispatch\_Status : data\_out   
MACS\_Control\_Drct : data\_out   
MFP\_Directive : data\_out   
LDT\_Directive : data\_out   
IDP\_Directive : data\_out   
PCD\_Directive : data\_out   
RDP\_Directive : data\_out   
RDC\_Directive : data\_out   
Directive : data\_in

## BODY:

Description of Process Accept the Directive from LPS operator and send the Directive to the target subsystem(s) or the MACS internal functions.

Assumptions Preconditions None.

Post conditions All Directives are sent to their appropriate destination.

Constraints None.

Functional Breakdown Accept the Directive keyed from LPS operator.

Forward the Directive to the appropriate subsystem(s) as shown in the following:

RDC\_Directive to RDCS   
RDP\_Directive to RDPS   
MFP\_Directive to MFPS   
PCD\_Directive to PCDS   
IPD\_Directive to IDPS   
LDT\_Directive to LDTS   
MACS\_Modify\_Schedule\_Drct to Modify Contact Schedule Function   
MACS\_Modify\_Conf\_Drct to Modify LPS Configuration Function   
MACS\_Control\_Drct to LPS System Control

When the RDP\_Directive.RDP\_Process\_Drct is issued to RDPS, then Send Contact\_Id to the Generate Metadata process.

Send the directive dispatching status as MACS\_Directive\_Dispatch\_Status to Report LPS Status function for display.

The Oracle SQL\*FORMS may be used to validate the inputs and route the directives.

NAME: 6.2;15

TITLE: Generate Metadata

INPUT/OUTPUT:   
Metadata\_File : data\_out   
MACS\_Metadata\_Generation\_Status : data\_out   
LDT\_Send\_DAN : data\_out   
Sub\_Intv : data\_in   
LPS\_Acct : data\_in   
Current\_Time : data\_in   
Valid\_WRS\_Parms : data\_in   
LPS\_Configuration : data\_in   
Contact\_Id : data\_in

## BODY:

Description of Process Create the Metadata\_File from LPS subinterval based quality and accounting information upon receipt of the Sub\_Intv information from the MFPS.

## Assumption

Preconditions The ACCA information and the quality and accounting files (LPS\_Acct) associated with current processed sub-intervals are completed upon receipt of the Sub\_Intv information from the MFPS. The latitude and longitude information for corner quadrants is available from Valid\_WRS\_Parms.

Post conditions The Metadata\_File is created on a subinterval basis and the LPS\_File\_List associated with this subinterval is also generated.

Constraints None

Functional Breakdown Receive the Contact\_Id. For each Sub\_Intv.Sub\_Intv\_Id identified by Contact\_Id, do the following:

Use Contact\_Id to identify the information within LPS\_Acct.RDC\_Acct necessary for the Metadata\_File.   
Use Contact\_Id to identify the information within LPS\_Acct.RDP\_Acct necessary for the Metadata\_File.   
Use Sub\_Intv.Sub\_Intv\_Id to identify the information within LPS\_Acct.MFP\_Acct necessary for the Metadata\_File.   
Use Sub\_Intv.Sub\_Intv\_Id to identify the information within LPS\_Acct.PCD\_Acct necessary for the Metadata\_File.   
Use Sub\_Intv.Sub\_Intv\_Id to identify the information within

LPS\_Acct.IDP\_Acct necessary for the Metadata\_File. Verify all of the quality and accounting stores in LPS\_Acct are completed for the current processed Sub\_Intv.Sub\_Intv\_Id.

Create the Metadata\_File\_Name using the LPS\_Configuration, File\_Version\_Number and the Sub\_Intv.MF\_Start\_Time identified by the current Sub\_Intv\_Id.   
Create the Metadata\_Header with the following information: Current\_Time, LPS\_Configuration.File\_Version\_Number, Sub\_Intv.Contact\_Id.LPS\_Hardware\_String\_Id, LPS\_Configuration.LPS\_Software\_Version\_Number, LPS\_Configuration.Spacecraft\_Id, LPS\_Acct.MFP\_Acct.Mjf\_VCDU\_QA.VCDU\_QA.ETM\_Data\_Format, LPS\_Configuration.Instrument\_Id, Sub\_Intv.Contact\_Id.Contact\_Start\_Time, LPS\_Acct.PCD\_Acct.Orbit\_Num, Sub\_Intv.MF\_Start\_Time, Sub\_Intv.MF\_Stop\_Time, LPS\_Acct.MFP\_Acct..Mjf\_VCDU\_QA.Mjf\_QA.Mjf\_Count, LPS\_Acct.PCD\_Acct.Num\_PCD\_MJF, LPS\_Acct.PCD\_Acct.First\_PCD\_MJF\_Time, LPS\_Acct.PCD\_Acct.WRS\_Path\_Nominal, LPS\_Acct.PCD\_Acct.WRS\_Row\_Nominal for first scene in subinterval determines Starting\_Row, LPS\_Acct.PCD\_Acct.WRS\_Row\_Nominal for last scene in subinterval determines Ending\_Row, LPS\_Acct.PCD\_Acct.PCD\_File\_Name, LPS\_Acct.IDP\_Acct.Browse\_File\_Names, LPS\_Acct.MFP\_Acct.Cal\_File\_Name, LPS\_Acct.MFP\_Acct.MSCD\_File\_Name, LPS\_Acct.IDP\_Acct.Band\_File\_Names, LPS\_Acct.IDP\_Acct.Bands\_Present, and LPS\_Acct.MFP\_Acct.Mjf\_VCDU\_QA.VCDU\_QA.ETM\_Data\_Format

Place the following information into the Metadata\_File:

Metadata\_Header,   
LPS\_Acct.MFP\_Acct.Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_BER\_Cnt,   
LPS\_Acct.MFP\_Acct.Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_Sync\_Err\_Cnt,   
LPS\_Acct.MFP\_Acct.Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_Rcvd\_Cnt,   
LPS\_Acct.MFP\_Acct.Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_Missing\_Cnt,   
Use the LPS\_Acct.MFP\_Acct.Mjf\_VCDU\_QA.VCDU\_QA. Mjf\_CADU\_RS\_Corr\_Cnt, and the LPS\_Acct.MFP\_Acct. Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_RS\_Uncorr\_Cnt to calculate VCDU\_Hdr\_Err\_Count,   
LPS\_Acct.MFP\_Acct.Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_BCH\_Corr\_Cnt,   
LPS\_Acct.MFP\_Acct.Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_BCH\_Uncorr\_Cnt,   
LPS\_Acct.MFP\_Acct.Mjf\_VCDU\_QA.VCDU\_QA.Mjf\_CADU\_BCH\_Bits\_Corr,   
LPS\_Acct.MFP\_Acct.Mjf\_Full\_Fill\_Cnt,   
LPS\_Acct.MFP\_Acct.Mjf\_Part\_Fill\_Cnt,   
LPS\_Acct.MFP\_Acct.Mjf\_Time\_Code\_Err\_Cnt,   
LPS\_Acct.PCD\_Acct.Minor\_Frame\_Acct.Failed\_PCD\_Votes added for each major frame in the PCD cycle

will provide the Failed\_PCD\_Votes,

LPS\_Acct.PCD\_Acct.Minor\_Frame\_Acct. Num\_PCD\_MNF\_Sync\_Errors added for each major frame in the PCD cycle will provide the Num\_PCD\_MNF\_Sync\_Errors,

LPS\_Acct.PCD\_Acct.Minor\_Frame\_Acct.Num\_PCD\_Filled\_MNF added for each major frame in the PCD cycle will provide the Num\_PCD\_Filled\_MNF,

LPS\_Acct.PCD\_Acct.Major\_Frame\_Acct.Num\_PCD\_Filled\_MJF added for each major frame in the PCD cycle will provide the Num\_PCD\_Filled\_MJF,

LPS\_Acct.PCD\_Acct.Major\_Frame\_Acct.Num\_Avail\_ADP,

LPS\_Acct.PCD\_Acct.Major\_Frame\_Acct.Num\_Rejected\_ADP,

LPS\_Acct.PCD\_Acct.Major\_Frame\_Acct.Num\_Missing\_ADP,

LPS\_Acct.PCD\_Acct.Major\_Frame\_Acct.Num\_Avail\_EDP,

LPS\_Acct.PCD\_Acct.Major\_Frame\_Acct.Num\_Rejected\_EDP,

LPS\_Acct.PCD\_Acct.Major\_Frame\_Acct.Num\_Missing\_EDP,

For each identified scene in LPS\_Acct.PCD\_Acct. PCD\_Scene\_Count provide the following:

LPS\_Acct.PCD\_Acct.Sub\_Intv\_Scene\_Num,

LPS\_Acct.PCD\_Acct.WRS\_Path\_Nominal,

LPS\_Acct.PCD\_Acct.WRS\_Row\_Nominal,

LPS\_Acct.PCD\_Acct.Scene\_Center\_Time,

LPS\_Acct.PCD\_Acct.Scene\_Center\_Scan\_Num,

Valid\_WRS\_Parms.Center\_Latitude,

Valid\_WRS\_Parms.Center\_Longitude,

Valid\_WRS\_Parms.Upper\_Left\_Corner\_Latitude,

Valid\_WRS\_Parms.Upper\_Left\_Corner\_Longitude,

Valid\_WRS\_Parms.Upper\_Right\_Corner\_Latitude,

Valid\_WRS\_Parms.Upper\_Right\_Corner\_Longitude,

Valid\_WRS\_Parms.Lower\_Left\_Corner\_Latitude,

Valid\_WRS\_Parms.Lower\_Left\_Corner\_Longitude,

Valid\_WRS\_Parms.Lower\_Right\_Corner\_Latitude,

Valid\_WRS\_Parms.Lower\_Right\_Corner\_Longitude,

LPS\_Acct.PCD\_Acct.Sun\_Azimuth,

LPS\_Acct.PCD\_Acct.Sun\_Elevation,

LPS\_Acct.IDP\_Acct.ACCA.CCA\_Quadrant1\_Score,

LPS\_Acct.IDP\_Acct.ACCA.CCA\_Quadrant2\_Score,

LPS\_Acct.IDP\_Acct.ACCA.CCA\_Quadrant3\_Score,

LPS\_Acct.IDP\_Acct.ACCA.CCA\_Quadrant4\_Score,

LPS\_Acct.IDP\_Acct.ACCA.CCA\_Aggregate\_Score,

LPS\_Acct.IDP\_Acct.Gain\_Change\_Flag,

LPS\_Acct.IDP\_Acct.Band\_Gain

Set LDT\_Send\_DAN.Contact\_Id to Contact\_Id

Set LDT\_Send\_DAN.Contact\_File\_Names.Sub\_Intv\_File\_Names. Metadata\_File\_Name to Metadata\_File\_Name

Set LDT\_Send\_DAN.Contact\_File\_Names.Sub\_Intv\_File\_Names. PCD\_File\_Name to LPS\_Acct.PCD\_Acct.PCD\_File\_Name.

Set LDT\_Send\_DAN.Contact\_File\_Names.Sub\_Intv\_File\_Names. Browse\_File\_Names to LPS\_Acct.IDP\_Acct. Browse\_File\_Names.

Set LDT\_Send\_DAN.Contact\_File\_Names.Sub\_Intv\_File\_Names.

Cal\_File\_Name to LPS\_Acct.MFP\_Acct.Cal\_File\_Name. Set LDT\_Send\_DAN.Contact\_File\_Names.Sub\_Intv\_File\_Names. MSCD\_File\_Name to LPS\_Acct.MFP\_Acct.

Set LDT\_Send\_DAN.Contact\_File\_Names.Sub\_Intv\_File\_Names. Band\_File\_Names to LPS\_Acct.IDP\_Acct.Band\_File\_Names.

Output the LDT\_Send\_DAN notification to the LDTS if the current Sub\_Intv\_Id is the last subinterval of the currently processed contact period identified by Contact\_Id.

Send the MACS\_Metadata\_Generation\_Status to Report LPS Status function for display.

## Reusability

The directive routing, status forwarding and message logging functions may be able to be reused from the existing projects.

NAME: 6.3;12

TITLE: Report LPS Status

INPUT/OUTPUT:   
LPS\_Status : data\_out   
LPS\_Journal : data\_out   
MACS\_Directive\_Dispatch\_Status : data\_in   
MACS\_Control\_Status : data\_in   
PCD\_Status : data\_in   
RDP\_Status : data\_in   
MFP\_Status : data\_in   
IDP\_Status : data\_in   
LDT\_Status : data\_in   
RDC\_Status : data\_in   
MACS\_Modify\_Config\_Status : data\_in   
MACS\_Modify\_Schedule\_Status : data\_in   
MACS\_Metadata\_Generation\_Status : data\_in

## BODY:

Description of Process Report or display the LPS\_Status to LPS operator.

Assumption Preconditions None.

Post conditions The LPS\_Status is displayed on the console to LPS operator.

Constraints None.

Functional Breakdown Receive incoming status messages from LPS Subsystems and other MACS functions. Report the received status messages to the LPS operator as LPS\_Status. Log the LPS\_Status message into the LPS\_Journal system log.

Reusability The LPS system monitoring function and the message logging function from PACOR II may be reusable.

NAME: 6.4;13

TITLE: Display or Print LPS Report

INPUT/OUTPUT:   
LPS\_Report : data\_out   
Report\_LDT\_File\_Xfer\_Sum : data\_in   
Report\_RDC\_Data\_Capture\_Sum : data\_in   
Report\_MFP\_L0R\_QA : data\_in   
Report\_RDP\_Return\_Link\_QA : data\_in

## BODY:

Description of Process Display or generate a hardcopy report to LPS operator for the specified summary or quality and accounting information.

## Assumption

Preconditions The summary or quality and accounting information is provided by LPS subsystems prior to display or report.

Post conditions The specified summary or quality and accounting information will be displayed on the console or printed in a hardcopy report.

Constraints None.

## Functional Breakdown

Report\_RDC\_Data\_Capture\_Sum, Report\_RDP\_Return\_Link\_QA, Report\_MFP\_L0R\_QA, Report\_LDT\_File\_Xfer\_Sum

Display or generate a hardcopy report for the received summary or quality and accounting information based on the report type specified in the received summary or quality and accounting information.

## Reusability

This function may be satisfied using Database Report writer package.

NAME: 6.5;7

TITLE: Modify LPS Configuration

INPUT/OUTPUT: MACS\_Modify\_Config\_Drct : data\_inout MACS\_Modify\_Config\_Status : data\_out MACS\_Modify\_Config\_Drct : data\_in

## BODY:

Description of Process Modify information in the LPS\_Configuration store.

Assumption Preconditions None.

Post conditions None.

Constraints None.

Functional Breakdown Verify the MACS\_Modify\_Config\_Drct input and make sure the individual field format and range of the entry are valid. Replace the existing LPS\_Configuration entry. Output the MACS\_Modify\_Config\_Status.

Reusability This process can be satisfied with Oracle SQL.

NAME: 6.6;9

TITLE: Modify Contact Schedule

INPUT/OUTPUT: Contact\_Schedules : data\_inout MACS\_Modify\_Schedule\_Status : data\_out MACS\_Modify\_Schedule\_Drct : data\_in

## BODY: BODY:

Description of Process Modify information in the Contact\_Schedules store.

Assumption Preconditions None.

Post conditions None.

Constraints None.

## Functional Breakdown

Verify the MACS\_Modify\_Schedule\_Drct input and make sure the individual field format and range of the entry are valid.

If we are modifying existing Contact\_Schedules information, then Replace the old Contact\_Schedules information with the new Contact\_Schedules information identified by MACS\_Modify\_Schedule\_Drct.Contact\_Schedule\_Id.

If we are adding new Contact\_Schedules information, then Insert the new Contact\_Schedules information into the Contact\_Schedules store assigning a new MACS\_Modify\_Schedule\_Drct.Contact\_Schedule\_Id.

If we are removing existing Contact\_Schedules information, then Remove the existing Contact\_Schedules information from the Contact\_Schedules store identified by MACS\_Modify\_Schedule\_Drct.Contact\_Schedule\_Id.   
Output the MACS\_Modify\_Schedule\_Status.

## Reusability

This process can be satisfied with Oracle SQL.

NAME: 6.7;6

TITLE: LPS System Control

INPUT/OUTPUT: MACS\_Control\_Status : data\_out MACS\_Control\_Drct : data\_in

## BODY:

Description of Process Perform LPS system level control activity.

Assumption Preconditions None.

Post conditions None.

Constraints None.

Functional Breakdown Bring up the LPS system if MACS\_Control\_Drct is a Startup. Shut down the LPS system if MACS\_Control\_Drct is a Shutdown.

Assign MACS\_Control\_Status the result of any action taken

Reusability None.

NAME: 6.8;3

TITLE: Monitor System Faults

INPUT/OUTPUT: LPS\_Status : data\_out LPS\_Journal : data\_in

## BODY:

Description of Process Allows the operator access to the Activity log for LPS.

Assumptions Preconditions None.

Postconditions None.

Constraints None.

Functional Breakdown Display the contents of LPS\_Journal as LPS\_Status.

Reusability This function can be performed by a text editor.

## 4.9.2 Performance Requirements

The following list summarizes the performance requirements allocated to the MACS:

4.9.2.1 The MACS software on each LPS string shall forward any directive to start/stop data capture or to generate a data receive summary to the RDCS within one second of its receipt from the operator.

4.9.2.2 The MACS software on each LPS string shall display a data receive summary for the most recently received raw wideband data within one second of its receipt from the RDCS.

4.9.2.3 The MACS software on each LPS string shall submit a data receive summary for the most recently received raw wideband data to a print queue within 1 second of its receipt from the RDCS.

4.9.2.4 The MACS software on each LPS string shall provide the capability to execute concurrently with all other LPS subsystems.

4.9.2.4.1 The MACS software on each LPS string shall begin to process metadata immediately upon receipt of required inputs.

4.9.2.4.2 The MACS software on each LPS string shall output a metadata file within 240 seconds of the time of receiving all required inputs.

4.9.2.5 The MACS software on each LPS string shall maintain data processing throughput performance for all Landsat 7 raw wideband data received with a BER of one bit error in 105 bits, without loss of level zero processed data and without retransmission.

4.9.2.6 The mean time to bring up the MACS software on any LPS string (from operating system boot to readiness to accept operator inputs) shall not exceed 12 minutes (based on a 15 minute estimate from RMA analysis and allowing 3 minutes for operator initiation and network latencies, 5 minutes for OS boot, 5 minutes for DBMS startup, and 2 minutes for LPS software start-up).

4.9.2.7 The time to bring up the MACS software on any LPS string (from operating system boot to readiness to accept operator inputs) shall not exceed twice the required mean time to bring up MACS software in 99 percent of all cases.

4.9.2.8 The MACS software on each LPS string shall output any periodic processing status information that it generates with a maximum latency of 30 seconds between outputs.

## 4.10 LPS Data Transfer Subsystem (LDTS)

This subsystem is responsible for sending a Data Availability Notification (DAN) to the LP DAAC about the availability of LPS files on a contact basis. Upon receiving a Data Transfer Acknowledgment (DTA), this subsystem is responsible for deleting the successfully transferred files. This subsystem is also responsible for generating a daily file transfer summary report upon request.

## 4.10.1 Functional Requirements

The following list summarizes the functional requirements allocated to the LDTS:

Interface with the LP DAAC to coordinate the transfer of LPS output files to the LP DAAC.

• notify LP DAAC on the availability of LPS files.

provide the capability to receive notification from LP DAAC on the successful receipt of transferred LPS files.

provide the capability to store LPS data files until confirmation of successful transfer is received from the LP DAAC.

provide a manual over-ride and protected capability to delete all LPS files on a specific contact period basis.

provide a manual over-ride and protected capability to retain all LPS files on-line on a specific contact period basis.

provide the capability to generate LPS file(s) transfer summary on a daily basis.

provide the capability to manually override the LPS automated functions.

• provide the capability to selectively enable or disable the Transfer LPS Files function.

## 4.10.1.1 Major Functions

The Generate DAN function receives the LDT\_Send\_DAN directive from the MACS and then retrieves information from the LDT\_Output\_File\_Info data store to build a data availability notification (DAN).

The DAN is passed to the Send DAN function which sends it to the LP DAAC. Sending DAN can be enabled or disabled by operator via the Control Send DAN function. The DAN will be resent upon operator's request (LDT\_Resend\_DAN\_Drct).

The Receive DTA function processes the DTA received from the LP DAAC and notifies the Delete LPS Files function to delete successfully transferred files. File deletions can be overridden by operator via the Retain LPS File function.

The LDT\_Output\_File\_Info data store is maintained by the Generate DAN, Delete LPS Files, Retain LPS Files and Receive DAT functions. It is used by the Generate Transfer Summary Report function to build and send to MACS a Report\_LDT\_File\_Xfer\_Sum.

The Transfer Files function handles file transfers between the LPS and LP DAAC.

The major functions of LDTS are depicted in the following data flow diagram.

## 4.10.1.2 Interface Requirements

The following two tables summarize the interface requirements for the LDTS:
<table><tr><td rowspan=1 colspan=1>Input Item Name</td><td rowspan=1 colspan=1>Source</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>Current_Time</td><td rowspan=1 colspan=1>TimeSource</td><td rowspan=1 colspan=1>System wide time source</td></tr><tr><td rowspan=1 colspan=1>LDT_Send_DAN</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Subinterval files complete notice</td></tr><tr><td rowspan=1 colspan=1>LDT_Directive</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>Control directives from operator.</td></tr><tr><td rowspan=1 colspan=1>Metadata_File</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>It contains LPS quality andaccounting information.</td></tr><tr><td rowspan=1 colspan=1>MSCD_File</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>It contains mirror scan correctiondata.</td></tr><tr><td rowspan=1 colspan=1>Cal_File</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>It contains calibration data foreach major frame.</td></tr><tr><td rowspan=1 colspan=1>Band_File</td><td rowspan=1 colspan=1>IDPS</td><td rowspan=1 colspan=1>A set of files of de-interleaveddata with one file per band.</td></tr><tr><td rowspan=1 colspan=1>Browse_File</td><td rowspan=1 colspan=1>IDPS</td><td rowspan=1 colspan=1>It contains reduced data-volumeimage files.</td></tr><tr><td rowspan=1 colspan=1>PCD_File</td><td rowspan=1 colspan=1>PCDS</td><td rowspan=1 colspan=1>It contains PCD major frames.</td></tr><tr><td rowspan=1 colspan=1>Transfer_Request</td><td rowspan=1 colspan=1>LP DAAC</td><td rowspan=1 colspan=1>Data transfer request</td></tr><tr><td rowspan=1 colspan=1>DTA</td><td rowspan=1 colspan=1>LP DAAC</td><td rowspan=1 colspan=1>Data transfer acknowledgment</td></tr></table>

Table 4.14 LDTS Interface Requirements - OUTPUT
<table><tr><td rowspan=1 colspan=1>Output Item Name</td><td rowspan=1 colspan=1>Destination</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>Report_LDT_File_Xfer_Sum</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>A summary report of LPS filetransfers.</td></tr><tr><td rowspan=1 colspan=1>DAN</td><td rowspan=1 colspan=1>LP DAAC</td><td rowspan=1 colspan=1>Data available notification sent toLP DAAC from LPS.</td></tr><tr><td rowspan=1 colspan=1>LDT_DAN_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>It indicates either a DAN has beensent or communication problems.</td></tr><tr><td rowspan=1 colspan=1>LDT_DTA_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>It indicates a DTA has beenreceived from LP DAAC.</td></tr><tr><td rowspan=1 colspan=1>[LDT_Retain_Files_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>It indicates success or failure ofan LDT_Retain_Files_Drct.</td></tr><tr><td rowspan=1 colspan=1>LDT_Delete_Files_Status</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>It indicates success or failure ofan LDT_Delete_Files_Drct.</td></tr><tr><td rowspan=1 colspan=1>LPS_Files</td><td rowspan=1 colspan=1>LP DAAC</td><td rowspan=1 colspan=1>The LPS level OR files transferredto the LP DAAC via file transferprotocols.</td></tr><tr><td rowspan=1 colspan=1>LPS_File_Transfer_Status</td><td rowspan=1 colspan=1>LP DAAC</td><td rowspan=1 colspan=1>The file transfer status generatedfrom the file transfer protocols.</td></tr></table>

## 4.10.1.3 Detailed Functional Requirements

This section contains the process specifications for the lowest level processes in the LDTS data flow diagrams.

NAME: 7.1;10

TITLE: Generate DAN

INPUT/OUTPUT: Time\_Available : data\_out Internal\_DAN : data\_out Contact\_Id : data\_out Contact\_File\_Names : data\_out LDT\_Send\_DAN : data\_in Current\_Time : data\_in

## BODY:

Description of Process This function constructs and sends a Data Availability Notice (DAN) to the LDTS "Send DAN" function.

Assumptions Preconditions None.

Post conditions None.

Constraints None.

Functional Breakdown Build an Internal\_DAN: Set Internal\_DAN.Contact\_Id to LDT\_Send\_DAN.Contact\_Id Set Internal\_DAN.Contact\_File\_Names to LDT\_Send\_DAN.Contact\_File\_Names

Create an LPS\_Output\_File\_Info entry Set LPS\_Output\_File\_Info.Contact\_Id to LDT\_Send\_DAN.Contact\_Id Set LPS\_Output\_File\_Info.Contact\_File\_Names to LDT\_Send\_DAN.Contact\_File\_Names. Set LPS\_Output\_File\_Info.Time\_Available to Current\_Time.

Send Internal\_DAN to "Send DAN" function.

## Reusability

Reuse of DDF and Pacor II's DAN functionality is a possibility.

NAME: 7.2

TITLE:Send DAN

INPUT/OUTPUT:   
DAN\_Suspended : data\_inout   
LDT\_DAN\_Status : data\_out   
DAN\_Transmission\_Time : data\_out   
DAN : data\_out   
LDT\_Resend\_DAN\_Drct : data\_in   
DAN\_Transfer\_State : data\_in   
Current\_Time : data\_in   
Contact\_File\_Names : data\_in   
Internal\_DAN : data\_in

## BODY:

Description of Process This function sends or resends a data availability notifications (DANs) to the LP DAAC. If sending DANs is disabled, the DAN is stored for sending once sending is enabled.

## Assumptions Assumptions

Preconditions None   
Post conditions None   
Constraints None

## Functional Breakdown

If DAN\_Transfer\_State is "ENABLED": If LDT\_Resend\_DAN\_Drct is received: Retrieve LDT\_Output\_File\_Info where LDT\_Output\_File\_Info.Contact\_Id equals LDT\_Resend\_DAN\_Drct.Contact\_Id Set DAN.Contact\_Id to LDT\_Resend\_DAN\_Drct.Contact.Id Set DAN.Contact\_File\_Names to LDT\_Output\_File\_Info.Contact\_File\_Names If LDT\_Output\_File\_Info.DAN\_Suspended is "SUSPENDED" then Update LDT\_Output\_File\_Info.DAN\_Suspended to "PROCESS".

If Internal\_DAN is received: Retrieve LDT\_Output\_File\_Info where LDT\_Output\_File\_Info.Contact\_Id equals Internal\_DAN.Contact\_Id Set DAN.Contact\_Id to Internal\_DAN.Contact\_Id Set DAN.Contact\_File\_Names to Internal\_DAN.Contact\_File\_Names

Send the DAN to the LP DAAC

Append Current\_Time to LDT\_Output\_File\_Info.DAN\_Transmission\_Time

list.

Send LDT\_DAN\_Status to MACS indicating the Contact\_Id and status of the DAN that was sent.

If DAN\_Transfer\_State is "DISABLED": If Internal\_DAN is received: Retrieve LDT\_Output\_File\_Info where LDT\_Output\_File\_Info.Contact\_Id equals Internal\_DAN.Contact\_Id If LDT\_Resend\_DAN\_Drct is received: Retrieve LDT\_Output\_File\_Info where LDT\_Output\_File.Contact\_Id equals LDT\_Resend\_DAN.Drct.Contact\_Id. Update LDT\_Output\_File\_Info.DAN\_Suspended to true Send LDT\_DAN\_Status to MACS indicating that DAN transfer is disabled and the DAN associated with Contact\_Id was not sent

## Reusability

Possible reuse of Pacor II/DDF code depending on the ICD between LPS and LP DAAC.

NAME: 7.3;10

TITLE: Receive DTA

INPUT/OUTPUT:   
Contact\_Id : data\_out   
LDT\_DTA\_Status : data\_out   
DTA\_Time\_Of\_Receipt : data\_out   
Current\_Time : data\_in   
DTA : data\_in

## BODY:

Description of Process This function extracts file transfer information from the input data transfer acknowledgment (DTA). It notifies MACS that a DTA was received and updates LPS\_Output\_File\_Info with the receipt time if the DTA indicates successful file transfer.

Assumptions Preconditions None.

Post conditions LPS\_Output\_File\_Info data store will be updated with the time of receipt of the DTA if DTA indicates success.

Constraints DTA format will be defined in the ICD between LPS and LP DAAC.

Functional Breakdown DTA indicates successful transfer of LPS files to LP DAAC: Append Current\_Time to LDT\_Output\_File\_Info.DTA\_Time\_Of\_Receipt for LDT\_Output\_File\_Info.Contact\_Id equal to DTA.Contact\_Id

Send Contact\_Id to "Delete LPS Files" function

Send MACS LDT\_DTA\_Status indicating successful transfer of files for contact DTA.Contact\_Id

DTA indicates unsuccessful transfer of LPS files to LP DAAC: Send MACS LDT\_DTA\_Status indicating unsuccessful transfer of files for contact DTA.Contact\_Id

Reusability None.

NAME: 7.4;7

TITLE: Transfer Files

INPUT/OUTPUT:   
LPS\_File\_Transfer\_Status : data\_out   
LPS\_Files : data\_out   
Transfer\_Request : data\_in   
Metadata\_File : data\_in   
PCD\_File : data\_in   
Browse\_File : data\_in   
Band\_File : data\_in   
Cal\_File : data\_in   
MSCD\_File : data\_in

## BODY:

Description of Process This function transfers LPS Output files to the LP DAAC in response to a request from LP DAAC.

## Assumptions

Preconditions None.

Postconditions None.

Constraints A COTS File transfer protocol (as per the ICD between LPS and LP DAAC) will be used.

## Functional Breakdown

Send LPS\_Files (consisting of Band\_File, PCD\_File, Browse\_File, Cal\_File, MSCD\_File, and Metadata\_File to the LP DAAC in response to receipt of a Transfer\_Request.   
Send LPS\_File\_Transfer\_Status, indicating the status of the requested file transfer operations, to the LP DAAC.

Reusability COTS software will be used.

NAME: 7.5;10

TITLE: Generate Transfer Summary Report

INPUT/OUTPUT:   
Report\_LDT\_File\_Xfer\_Sum : data\_out   
LDT\_Rpt\_File\_Xfer\_Sum\_Drct : data\_in   
Current\_Time : data\_in   
LDT\_Output\_File\_Info : data\_in

## BODY:

Description of Process This function generates the LPS file transfer summary report upon receiving a request from the MACS.

Assumptions Preconditions None.

Post conditions None.

Constraints None.

Functional Breakdown Calculate Report\_Begin\_Time equal to midnight of the day represented by LDT\_Rpt\_File\_Xfer\_Sum\_Drct.Date Calculate Report\_End\_Time equal the point in time which is the earlier of 1) Current\_Time 2) Midnight of the day following LDT\_Rpt\_File\_Xfer\_Sum\_Drct.Date

Set Report\_LDT\_File\_Xfer\_Sum.Current\_Time equal to Current\_Time Set Report\_LDT\_File\_Xfer\_Sum.Date\_Of\_Report\_Data to Report\_LDT\_File\_Xfer\_Sum.Date

Set Report\_LDT\_File\_Xfer\_Sum.Available\_File\_Names to all LDT\_Output\_File\_Info.Contact\_File\_Names where LDT\_Output\_File\_Info.Time\_Available is less than or equal to Report\_End\_Time, There are no times in the LDT\_Output\_File\_Info. DAN\_Transmission\_Time list less than or equal to Report\_End\_Time, and any value in LDT\_Output\_File\_Info.Time\_Deleted is greater than Report\_End\_Time.

Set Report\_LDT\_File\_Xfer\_Sum.Available\_L0R\_File\_Count equal to the number of L0R files in Report\_LDT\_File\_Xfer\_Sum.Available\_File\_Names   
Set Report\_LDT\_File\_Xfer\_Sum.Available\_Metadata\_File\_Count equal to the number of Metadata files in Report\_LDT\_File\_Xfer\_Sum.Available\_File\_Names   
Set Report\_LDT\_File\_Xfer\_Sum.Available\_Browse\_File\_Count equal to the number

of Browse files in Report\_LDT\_File\_Xfer\_Sum.Available\_File\_Names

Set Report\_LDT\_File\_Xfer\_Sum.Online\_File\_Names to all LDT\_Output\_File\_Info.Contact\_File\_Names where There is at least one time in the LDT\_Output\_File\_Info.DAN\_Transmission\_Time list less than or equal to Report\_End\_Time, and there are no times in the LDT\_Output\_File\_Info. DTA\_Time\_Of\_Receipt list less than or equal to Report\_End\_Time, and any value in LDT\_Output\_File\_Info.Time\_Deleted is greater than Report\_End\_Time.

Set Report\_LDT\_File\_Xfer\_Sum.Online\_L0R\_File\_Count equal to the number of L0R files in Report\_LDT\_File\_Xfer\_Sum.Online\_File\_Names

Set Report\_LDT\_File\_Xfer\_Sum.Online\_Metadata\_File\_Count equal to the number of Metadata files in Report\_LDT\_File\_Xfer\_Sum. Online\_File\_Names

Set Report\_LDT\_File\_Xfer\_Sum.Online\_Browse\_File\_Count equal to the number of Browse files in Report\_LDT\_File\_Xfer\_Sum.Online\_File\_Names

Set Report\_LDT\_File\_Xfer\_Sum.Transmitted\_File\_Names to all LDT\_Output\_File\_Info.Contact\_File\_Names where LDT\_Output\_File\_Info.DTA\_Time\_Of\_Receipt is greater than or equal to Report\_Start\_Time and less than Report\_End\_Time.

Calculate Report\_LDT\_File\_Xfer\_Sum.Volume\_Of\_Retained\_Data Calculate Report\_LDT\_File\_Xfer\_Sum.Available\_Retention\_Space

Send Report\_LDT\_File\_Xfer\_Sum to the MACS.

## Reusability

System Software will be used to calculate Volume\_Of\_Retained\_Data and Available\_Retention\_Space.

NAME: 7.6;14

TITLE: Delete LPS Files

## INPUT/OUTPUT:

Time\_Deleted : data\_out   
LDT\_Delete\_Files\_Status : data\_out   
LDT\_Delete\_Files\_Drct : data\_in   
Current\_Time : data\_in   
Metadata\_File : data\_in   
PCD\_File : data\_in   
Browse\_File : data\_in   
Band\_File : data\_in   
Cal\_File : data\_in   
MSCD\_File : data\_in   
Marked\_For\_Retention : data\_in   
Contact\_Id : data\_in

## BODY:

Description of Process This function deletes LPS files for a contact period that has not been marked for retention. The entry in LDT\_Output\_File\_Info corresponding with the Contact\_Id is time stamped with the time the Contact\_Id's files were deleted.

## Assumptions

Preconditions None.

Post conditions LPS files for the given Contact\_Id have been deleted. LDT\_File\_Info is updated with the time of deletion.

Constraints None.

## Functional Breakdown

If LDT\_Delete\_Files\_Drct message received from MACS:   
(this means override any file retention previously specified) For each file in Metadata\_File, PCD\_File, Cal\_File, MSCD\_File, Browse\_File, and Band\_File associated with LDT\_Delete\_Files\_Drct.Contact\_Id : Delete the file from LPS storage. Set LDT\_Output\_File\_Info.Time\_Deleted to Current\_Time for LDT\_Output\_File\_Info.Contact\_Id equal to Contact\_Id

If Contact\_Id from "Receive DTA" function is received Retrieve LDT\_Output\_File\_Info.Marked\_For\_Retention for LPS\_Output\_File\_Info.Contact\_Id equal to Contact\_Id If Marked\_For\_Retention indicates "DELETE" then For each file in Metadata\_File, PCD\_File, Cal\_File, MSCD\_File,

Browse\_File, and Band\_File associated with   
Contact\_Id Delete the file from LPS storage.   
Set LDT\_Output\_File\_Info.Time\_Deleted to Current\_Time for LDT\_Output\_File\_Info.Contact\_Id equal to Contact\_Id

Send a status message containing Contact\_Id to MACS in LDT\_Delete\_Files\_Status . Reusability None.

NAME: 7.7;11

TITLE: Retain LPS Files

INPUT/OUTPUT: Marked\_For\_Retention : data\_out LDT\_Retain\_Files\_Status : data\_out LDT\_Retain\_Files\_Drct : data\_in

## BODY:

Description of Process This function marks LPS output files associated with a Contact\_Id for retention. The files must then be manually deleted or deleted by a delete directive from the MACS.

Assumptions Preconditions None.

Post conditions None.

Constraints None.

Functional Breakdown If there exists an entry in LDT\_Output\_File for LDT\_Retain\_Files\_Drct.Contact\_Id and it does not have a value for Time\_Deleted: Retrieve LPS\_Output\_File\_Info where LPS\_Output\_File\_Info.Contact\_Id is equal to LDT\_Retain\_Files\_Drct.Contact\_Id.

Update LDT\_Output\_File\_Info.Marked\_For\_Retention to "RETAIN"

Send a status message containing Contact\_Id as LDT\_Retain\_Files\_Status to the MACS

There is no entry in LDT\_Output\_File\_Info for LDT\_Retain\_File\_Drct.Contact\_Id or there is one but it has a value for Time\_Deleted: Send LDT\_Retain\_Files\_Status to the MACS containing LDT\_Retain\_Files\_Drct.Contact\_Id and an indication that the files were not found.

Reusability None.

NAME: 7.8;9

TITLE: Control Send DAN

INPUT/OUTPUT:   
LDT\_Resend\_DAN\_Drct : data\_out   
DAN\_Transfer\_State : data\_out   
LDT\_Enable\_File\_Xfer\_Drct : data\_in   
LDT\_Disable\_File\_Xfer\_Drct : data\_in   
DAN\_Suspended : data\_in   
Contact\_Id : data\_in

## BODY:

Description of Process This function maintains a flag which indicates whether or not LPS DAN transfer is enabled.

Assumptions Preconditions None.

Postconditions None.

Constraints None.

LDT\_Enable\_File\_Xfer\_Drct is received: Update DAN\_Transfer\_State to indicate that LPS DAN transfer is enabled. For each Contact\_Id in LPS\_Output\_File\_Info where LDT\_Output\_File\_Info.DAN\_Suspended is "SUSPENDED" Set LDT\_Resend\_DAN\_Drct.Contact\_Id to Contact\_Id Send LDT\_Resend\_DAN\_Drct to LDTS "Send DAN"

LDT\_Disable\_File\_Xfer\_Drct is received: Update DAN\_Transfer\_State to indicate that LPS DAN transfer is disabled.

Reusability None.

## 4.10.2 Performance Requirements

The following list summarizes the performance requirements allocated to the LDTS:

4.10.2.1 The LDTS software on each LPS string shall provide the capability to transfer the equivalent of any combination of the format 1 and format 2 portions of 125 Landsat 7 ETM+ scenes of wideband data per day (approximately 25-30 GB per day). [4.1.3]

4.10.2.2 The LDTS software on each LPS string shall provide the capability to execute concurrently with all other LPS subsystems.

4.10.2.2.1 The LDTS software on each LPS string shall output a DAN within 240 seconds of the time of receiving all required inputs.

4.10.2.3 The LDTS software on each LPS string shall provide the capability to reprocess a maximum of 10% of a string's daily input volume of wideband data (approximately 12.5 scenes or 2.5-3 GB per day).

4.10.2.4 The LDTS software on each LPS string shall maintain data processing throughput performance for all Landsat 7 raw wideband data received with a BER of one bit error in 105 bits, without loss of level zero processed data and without retransmission.

4.10.2.5 The LDTS software on each LPS string shall provide the capability to transfer the string's daily volume of LPS output files to the LP DAAC at an average aggregate rate of 10 Mbps.

4.10.2.6 The LDTS software on each LPS string shall output any periodic processing status information that it generates with a maximum latency of 30 seconds between outputs.

## 5.0 Database Analysis

This section presents the results of LPS database design during the software requirement definition phase. The requirement definition phase includes requirement collection and analysis, conceptual design, and preliminary logical design as described in the following paragraphs. The LPS database design follows the standard database methodology which encompasses five major steps as illustrated in Figure 5.1. The methodology is consistent with SEAS System Development Methodology (SSDM). The design process consists of two parallel activities at each step: (1) Data view - the design of data content and structure of the database; (2) Process view - the design of processing and software application. Both views are described for each step of the process.

![](images/e69a5d2c8aadb9aa3149d521f39abd13bc189f3c2bc818661bcd709e958c10d7.jpg)  
Figure 5.1 LPS Database Design Approach

Requirement Collection & Analysis - This step is to identify and analyze the intended uses of the database. From the data point of view, this step identifies the LPS information to be stored in the database. From the processing perspective, this step analyzes the functional, performance, operational, and programmatic requirements of the LPS database. This step has been completed during the software requirement definition phase.

Conceptual Design - This step is to create a high level data model which is Database Management System (DBMS) independent. From the data point of view, this step examines the data requirements resulting from the previous step and produces a conceptual database model which consists of Entity Relationship Diagrams (ERDs). From the processing perspective, this step examines the interaction between LPS subsystems and the database, and produces subsystem level Create, Retrieve, Update, and Delete (CRUD) matrices. This step has been completed during the software requirement definition phase.

Logical Design - This step is to create a logical data model for a relational DBMS. From the data point of view, this step creates logical schemata and constraints to represent entities and relationships from the ERDs. Principles of normalization are applied to create well-structured schemata. From the processing perspective, this step produces functional CRUD matrices and database interface diagrams that describe the interaction between main processes within a subsystem and the database. This step also performs a preliminary analysis of data usage, performance constraints, and storage requirements. Part of this step has been completed during the software requirement definition phase while the rest will be continued in the next phase.

Physical Design - This step is to select specific storage structures and access methods for the database. From the data point of view, this step determines storage structures such as tables, views, indices, and organizations of database information. From the processing perspective, this step further analyzes data usage and performance constraints which leads to the determination of access methods.

Implementation - This step implements the database. From the data point of view, this step physically creates the LPS databases, tables, views, and indices through Data Definition Language (DDL) and Storage Definition Language (SDL) statements. From the processing perspective, this step implements database applications. Database transactions are examined and corresponding program code with embedded Structured Query Language (SQL) commands are written and tested. Once the transactions are ready, the database will be populated.

The Cadre Teamwork Information Modeling (IM) tool is used during the design process. Teamwork/IM is an integrated toolset that helps database engineers model the entities, relationships, and attributes of all LPS data at the conceptual level. The tool is used to:

• Create an LPS conceptual model consisting of entity relationship diagrams.

• Ensure the completeness and consistency of database design.

Generate code to create database tables and to enforce integrity constraints.

• Support documentation production.

Simplify the maintenance effort by easing impact analysis and change implementation.

• Enhance configuration management by maintaining baselines.

## 5.1 Requirement Analysis and Conceptual Design

The purpose of database requirements analysis is to identify and analyze the intended uses of the database. This includes the identification of the information to be stored in the database and the analysis of the functional, performance, operational, and programmatic requirements of the database. Conceptual design creates a high level data model which consists of ERDs and examines the interaction between LPS subsystems and the database. This section presents the results of the requirement analysis and conceptual design phase.

## 5.1.1 Functional Requirement Analysis

This section presents a functional overview of the information tracking requirements for the LPS. The functions are described in terms of their interactions with the database. The functions are based on the LPS subsystems and functions presented in section 3 of Landsat 7 Processing System (LPS) System Design Specification (SDS).

## 5.1.1.1 Raw Data Capture Subsystem (RDCS)

The Raw Data Capture Subsystem (RDCS) captures and manages raw wideband data received from the LGS. Each LGS channel's data stream for a contact period is captured to the on-line disk. The data set is subsequently copied to removable media. Upon request, the RDCS retrieves a raw wideband data set from removable media and returns it to the on-line storage for reprocessing. On request, the RDCS generates a data receive summary for a specified raw wideband data set. The interactions between the RDCS and the LPS database are as follows:

The RDCS retrieves the LPS configuration parameters such as the LPS hardware string identification and the LGS channel associated with the LPS string from the database when the RDCS starts up.

The RDCS captures a raw wideband data bit stream for a single channel from the LGS and outputs the stream as a byte stream data set to an on-line raw wideband data store. At the end of the contact period, the subsystem collects and stores a contact summary describing the contact in the database.

Upon request, the RDCS queries the database and generates a contact data receive summary for displaying and printing.

Upon request, the RDCS retrieves the requested raw wideband data from removable media to the on-line storage for reprocessing. If not already present, contact summary information is collected and stored in the database.

## 5.1.1.2 Raw Data Processing Subsystem (RDPS)

The Raw Data Processing Subsystem (RDPS) inputs the rate buffered wideband data from the on-line data store and performs CCSDS Advanced Orbiting Systems (AOS) Grade 3 service on the received Channel Access Data Units (CADUs). This subsystem performs frame synchronization and Pseudo-Random Noise (PN) decoding of the received CADUs, Cyclic Redundancy Check (CRC) on VCDUs, and Reed-Solomon (RS) error detection and correction of VCDU headers. It also performs the BCH error detection and correction processing. The RDPS collects and generates raw data processing accounting and subsystem status information. The interactions between the RDPS and the LPS database are as follows:

The RDPS receives CCSDS processing parameters and thresholds, transforms them into the subsystem's internal format (if necessary), and stores them in the database.

The RDPS retrieves CCSDS parameters and thresholds for the frame synchronization processing. In addition, thresholds are also retrieved and used during the CCSDS AOS Grade 3 service and BCH processing.

The RDPS processes the raw wideband data set for a contact period. It uses the CCSDS parameters and thresholds retrieved from the database for its processing and error reporting. The RDPS accumulates and collects quality and accounting information on a contact basis. The collected quality and accounting information is then stored in the database.

Upon request, the RDPS queries the database and generates return link quality and accounting summary for displaying and printing.

## 5.1.1.3 Major Frame Processing Subsystem (MFPS)

The Major Frame Processing Subsystem (MFPS) processes annotated CADUs. This subsystem provides the functionality to synchronize the major frames, extract major frame times, deinterleave band data, reverse band data if necessary, and align band data. It is also responsible for generating the Calibration and Mirror Scan Correction files. In addition, it determines subinterval boundaries and extracts and provides PCD information to the PCDS subsystem. The MFPS also collects and generates Level 0R accounting and subsystem status information. The interactions between the MFPS and the LPS database are as follows:

The MFPS receives, validates, and stores the sensor alignment information, the subinterval threshold, VCDU processing thresholds, major frame processing thresholds, and scan line processing thresholds in the database.

The MFPS retrieves and uses the subinterval threshold to determine subintervals. Subintervals generated are stored in the database which are used by other subsystems.

The MFPS retrieves and uses thresholds for error reporting during its processing.

The MFPS retrieves and uses sensor alignment information for band alignment processing.

The MFPS collects Level 0R quality and accounting information on a subinterval basis. Information collected is stored in the database which is used by the MACS for metadata generation.

Upon request, the MFPS queries the database and generates Level 0R quality and accounting information for displaying and printing.

## 5.1.1.4 PCD Processing Subsystem (PCDS)

The PCD Processing Subsystem (PCDS) processes the Payload Correction Data (PCD). This subsystem is responsible for performing PCD byte majority voting, PCD major frame building, and PCD file generation. In addition, it identifies scenes using the Worldwide Reference System (WRS), calculates sun azimuth and elevation information, and extracts ETM+ calibration door events. The PCDS also collects and generates PCD accounting and subsystem status information. The interactions between the PCDS and the LPS database are as follows:

The PCDS receives, validates, and stores the frame fill values, frame quality parameters, error report thresholds, and scene calculation parameters in the database. In addition, the WRS scene information is also stored in the database.

The PCD retrieves and uses the frame fill values and frame quality parameters during the process of assembling PCD cycles.

• The PCD retrieves and uses error report thresholds for error reporting during its processing.

The PCD retrieves and uses scene calculation parameters and the WRS information to identify WRS scenes and calculate sun azimuth and elevation. Calculated scene and sun information is stored in the database and used by other subsystems.

The PCDS collects quality and accounting information during its processing of PCD data. Collected quality and accounting information is stored in the database and used by the MACS for metadata generation.

## 5.1.1.5 Image Data Processing Subsystem (IDPS)

The Image Data Processing Subsystem (IDPS) performs general LPS image data processing. The IDPS generates Level 0R instrument data files and browse files. It is also responsible for determining cloud coverage on a scene quadrant and full scene basis. The IDPS also collects and generates IDPS accounting and subsystem status information. The interactions between the IDPS and the LPS database are as follows:

The IDPS receives, validates, and stores band parameters for browse and Automatic Cloud Cover Assessment (ACCA) in the database.

The IDPS retrieves and uses subinterval information and band parameters to generate the browse files.

• The IDPS retrieves and uses subinterval information to generate the band files.

The IDPS retrieves and uses subinterval information and band parameters for its ACCA processing. ACCA scores are generated and stored in the database to be included in the metadata file.

The IDPS collects quality and accounting information during its processing. The collected information is stored in the database and used by the MACS for metadata generation.

## 5.1.1.6 Management and Control Subsystem (MACS)

The Management and Control Subsystem (MACS) provides an interface through which operations personnel can control the system operations, monitor overall system performance, access system accounting information, and manage the configuration parameters and thresholds which are used to drive system processing. The MACS also provides capabilities to generate metadata files and accounting information. The interactions between the MACS and the LPS database are as follows:

The MACS manages the LPS system configuration parameters in the database. The subsystem allows the operator to update the LPS system configuration parameters.

• The MACS allows the operator to update the contact schedules.

The MACS is responsible for generating metadata files. During the metadata file generation process, the MACS retrieves system configuration parameters, Level 0R quality and accounting information, PCD quality and accounting information, browse and band file accounting information, ACCA scores, WRS scene information, and subinterval data to generate metadata files on a subinterval basis. Metadata accounting and LPS file information is also generated and stored in the database for subsequent processing.

## 5.1.1.7 LPS Data Transfer Subsystem (LDTS)

The LPS Data Transfer Subsystem (LDTS) coordinates the transfer of LPS files to the LP DAAC over supported network connections. The LDTS is also responsible for overseeing the LPS file transmission, maintaining the status of all LPS files, managing the LPS output data store, and generating a file transfer summary. The interactions between the LDTS and the LPS database are as follows:

The LDTS retrieves and uses configuration parameters and LPS file information from the database for the Data Availability Notice (DAN) generation. The LPS file information is organized on a contact basis.

The LDTS maintains the status of all LPS files in the database. The status of LPS files is updated frequently to reflect Data Transfer Acknowledgments (DTAs) from the LP DAAC and directives from the MACS.

The LDTS is responsible for managing the LPS output data storage. It retrieves the status of LPS files from the database when deciding whether to retain or delete certain LPS files.

The LDTS retrieves and uses the LPS file information in the database to generate file transfer summaries.

## 5.1.2 Performance Requirement Analysis

Since all of the LPS subsystems interact with the database, the performance requirements for LPS subsystems include database performance considerations. Main factors affecting the database performance are discussed in the following subsections.

## 5.1.2.1 Response Time

The performance of the database is a part of the LPS performance. To provide the capability to process received wideband data at a minimum rate of 7.5 Mbps, the database access time must be minimized and optimized. To achieve this the LPS database must support the following capabilities:

Storage Optimization - Distribution of database tables over different disk drives where speed of disk reads and writes is crucial.

Indexing - Access structures which are used by applications to speed up the retrieval of records in response to certain search conditions.

Viewing - Virtual tables in which data from underlying base tables are combined so that applications can work with just one virtual table instead of the several or more complete base tables.

Query optimization - Heuristic and cost-based query optimization mechanisms to improve the efficiency of query execution.

Stored Procedures - Named and precompiled set of SQL statements which are stored in the server's data dictionary and can be executed by applications through names.

De-normalization - A process in which columns belonging to one table is redundantly defined in another table to reduce or eliminate the need to query the original table.

## 5.1.2.2 Reliability, Maintainability, and Availability (RMA)

The RMA of the database is a part of the RMA of the LPS. To support LPS operations 24 hours per day, 7 days per week, on a continuous basis, to provide an Operational Availability (Ao) of 0.96 or better, to achieve a mean time to restore (MTTRes) capability of 4 hours or better, and to comply with the requirement of not exceeding twice the required MTTRes in 99 percent of failure occurrences, the LPS DBMS must support the following capabilities:

• On-line backups and recovery

• On-line archiving

• Mirroring of critical database files (TBD)

## 5.1.2.3 Data Integrity

Data integrity is a data quality issue. Four categories of data integrity must be specified and enforced through appropriate mechanisms:

Entity integrity - Integrity that guarantees all primary key attribute values are not null. This capability should be supported by the DBMS.

Domain integrity - Integrity that enforces attribute values to adhere to the underlying application domain definitions. This capability should be supported by the DBMS.

Referential integrity - Integrity that guarantees the existence and correctness of the required relationship between two entities. This capability should be supported by the DBMS.

LPS application integrity - Integrity that protects the validity of attribute values. This capability is not provided by the DBMS and requires application software.

## 5.1.3 Operational Requirement Analysis

The LPS database must comply with the general operational requirements for the LPS.

## 5.1.3.1 Security

The LPS administrative function must provide security features to control how a database is accessed and used. Database security can be accomplished at multiple levels from applications to specific users by defining constraints that are stored in the data dictionary.

To gain access to the LPS database, each user must supply an account ID and password.

Access and use of actual LPS data objects such as tables, views, indices, and stored procedures will be controlled by grants on these database objects. This is accomplished by defining what data objects are available to each user, user group, or application. These constraints are stored in the LPS data dictionary.

## 5.1.3.2 Backup and Recovery

The LPS administrative function must be able to regularly schedule backups of all or selected parts of the database while the database is operational, and be able to perform these backups on demand. Critical database tables and files must be backed up more frequently.

In the event of a failure in LPS, if there has been no destruction of the data storage devices, normal restart procedures will restore the database to a state that is ready to begin the processing.

If a data storage device was destroyed, the data on that device will be restored from a backup copy. The data will be restored to the time of the backup. Modifications of critical data files that were applied after the backup will be reapplied by the DBMS if the mirrored log files are available.

## 5.1.3.3 Archival and Restoral

As historical tables grow large, they can begin to affect database performance. Utilities to copy historical data onto archival storage and to delete them from the active database should be supported. Historical data will be maintained on the active database for up to a TBR period.

## 5.1.4 Programmatic Requirement Analysis

Each LPS subsystem interacts with the database. To permit efficient and effective programming, the LPS DBMS will:

• Be a relational database.

• Comply with ANSI/ISO SQL.

• Interface with the C language through embedded SQL.

• Provide capabilities to generate and access stored procedures.

Automated routines and user interface facilities will be implemented to support the population of LPS database.

## 5.1.5 High Level Entity Relationship Model

The LPS Entity Relationship (ER) model is a conceptual representation of the data for LPS application. The ER model is expressed in terms of entities in the LPS environment, the relationships or associations among those entities, and the properties of the entities and their relationships. Entities represent data items that play a functional role in the LPS application and have their own set of attributes. Table 5-1 contains a description of each LPS entity identified during the conceptual design process. The attributes of each entity are analyzed and described in section 5.2. Note that new entities may be added and existing entities may be modified, merged, or split as the project progresses and the definitions of entities become more precise.

Table 5.1 LPS Entity Descriptions (1 of 2)
<table><tr><td rowspan=1 colspan=1>Entity Name</td><td rowspan=1 colspan=1>Entity Description</td></tr><tr><td rowspan=1 colspan=1>Contact_Schedules</td><td rowspan=1 colspan=1>A set of contact periods containing the start and stoptimes when Landsat 7 spacecraft down links the wideband data to the LGS. The schedule is coming fromthe LGS in a hard copy form.</td></tr><tr><td rowspan=1 colspan=1>IDP_Acct</td><td rowspan=1 colspan=1>Aggregate accounting information for the IDPSwhich includes band files, browse files, and ACCAaccount information on a subinterval basis.</td></tr><tr><td rowspan=1 colspan=1>LDT_Output_File_Info</td><td rowspan=1 colspan=1>All state information about LPS output files that are ofconcern to LDTS.</td></tr><tr><td rowspan=1 colspan=1>LPS_Configuration</td><td rowspan=1 colspan=1>The set of parameters used to configure the LPS.Some parameters are used when the system starts upwhile others are used during the processing.</td></tr><tr><td rowspan=1 colspan=1>MFP_Acct</td><td rowspan=1 colspan=1>An aggregate accounting information from the MFPSwhich includes the Level OR quality and accountinginformation on a subinterval basis.</td></tr><tr><td rowspan=1 colspan=1>PCD_Acct</td><td rowspan=1 colspan=1>An aggregate accounting information from the PCDSwhich includes the processed PCD quality andaccounting information on a subinterval basis.</td></tr></table>

Table 5.1 LPS Entity Descriptions (2 of 2)
<table><tr><td rowspan=1 colspan=1>Entity Name</td><td rowspan=1 colspan=1>Entity Description</td></tr><tr><td rowspan=1 colspan=1>RDC_Acct</td><td rowspan=1 colspan=1>Raw data capture accounting information on acontact basis.</td></tr><tr><td rowspan=1 colspan=1>RDP_Acct</td><td rowspan=1 colspan=1>An aggregate accounting information from the RDPSwhich includes return link quality and accountinginformation on a contact basis.</td></tr><tr><td rowspan=1 colspan=1>Sub_Intv</td><td rowspan=1 colspan=1>A list of subinterval information generated by theMFPS and used by the PCDS, IDPS, and MACS togenerate LPS files.</td></tr><tr><td rowspan=1 colspan=1>Valid_Band_Parms</td><td rowspan=1 colspan=1>An aggregate information which includes bandparameters and reduction ratio for browse and ACCAprocessing.</td></tr><tr><td rowspan=1 colspan=1>Valid_CCSDS_Parms</td><td rowspan=1 colspan=1>A list of parameters that controls CCSDS framesynchronization and bit slip correction.</td></tr><tr><td rowspan=1 colspan=1>Valid_MFP_Parms</td><td rowspan=1 colspan=1>The validated MFPS setup parameters.</td></tr><tr><td rowspan=1 colspan=1>Valid_MFP_Thres</td><td rowspan=1 colspan=1>The validated MFPS threshold values.</td></tr><tr><td rowspan=1 colspan=1>Valid_PCD_Parms</td><td rowspan=1 colspan=1>The validated PCD parameters used in processing PCDdata.</td></tr><tr><td rowspan=1 colspan=1>Valid_PCD_Thres</td><td rowspan=1 colspan=1>The validated PCD threshold parameters used inprocessing PCD data.</td></tr><tr><td rowspan=1 colspan=1>Valid_RDP_Thres</td><td rowspan=1 colspan=1>Validated RDP processing thresholds.</td></tr><tr><td rowspan=1 colspan=1>Valid_Scene_Parms</td><td rowspan=1 colspan=1>The validated general mission information andparameters provided by IAS and used to calculate thelongitude, latitude, the WRS scene Id and sunelevation and azimuth.</td></tr><tr><td rowspan=1 colspan=1>Valid_WRS_Parms</td><td rowspan=1 colspan=1>The validated Worldwide Reference System tablecontaining the information for each WRS scene.</td></tr></table>

The LPS ER model is expressed as ERDs, which are graphical representations of the ER model as illustrated in Figure 5.2. In addition to entities described above, relationships are also included in the diagram. The relationships represent the association between the instances of one or more entities that are of interest to the LPS. For each relationship, there is a cardinality associated with it. The cardinality describes the number of instances of one entity that can be associated with each instance of the entity to which it relates. For instance, there is more than one scene information (Scene\_Parms) for each subinterval (Sub\_Intv) while there is only one MFPS accounting information (MFP\_Acct) for each subinterval.

## 5.2 Logical Design

The logical design process is concerned with transforming the ERDs from the conceptual design phase to a logical relational model. Four major activities were performed during the logical design phase.

1. Represent entities. Each entity in the ERDs is represented as a logical schema in the relational data model. Candidate and primary keys are determined. The candidate keys are the sets of attributes that uniquely identify one occurrence of an entity. The predominant set of key attributes is the primary key.

2. Represent relationships. Each relationship in the ERDs is represented in the relational data model either by making the primary key of one logical schema a foreign key of another logical schema or by creating a separate logical schema. A foreign key is an attribute that appears as a nonkey attribute in one schema and as a primary key attribute in another schema.

3. Normalize the schemata. The logical schemata that are created in step 1 and 2 may have unnecessary redundancy and may be subject to anomalies when they are updated. Normalization is a process that refines the logical schemata to avoid these problems.

4. Merge the schemata. In some cases schemata may be redundant that must be merged to remove the redundancy.

The result of logical design is used as the foundation for the physical database design.

## 5.2.1 Logical Schema Definitions

To create well structured schemata that contain a minimum amount of redundancy and allow users to insert, modify, and delete database information without errors or inconsistencies, normalization principles are applied during the logical design process. The steps in normalization are illustrated in Figure 5.3.

![](images/da5abd27c1fa28cef74e112b4fac411a2d18d136c59c13c49e6496c19acfefcf.jpg)  
Figure 5.3 Normalization Steps

Most of the LPS logical schemata are normalized to the standard Boyce-Codd normal form. Some of the schemata are not normalized due to the fact that their attributes are yet TBD or TBR. Normalization and merging of schemata will continue until all schemata are well structured. The LPS logical schemata as of this phase are listed in Table 5.2. The primary key columns are identified by asterisks (\*). Note that the attributes and primary keys of some threshold schemata are not yet determined due to incompleteness of schema definitions.

Table 5.2 LPS Logical Schema Definitions (1 of 8)
<table><tr><td rowspan=1 colspan=1>Schema Name</td><td rowspan=1 colspan=1>Attribute Name</td><td rowspan=1 colspan=1>Attribute Description</td></tr><tr><td rowspan=3 colspan=1>Contact_Schedules</td><td rowspan=1 colspan=1>*Contact_Schedule_Id</td><td rowspan=1 colspan=1>Contact schedule identification</td></tr><tr><td rowspan=1 colspan=1>Contact_Schedule_Start_Time</td><td rowspan=1 colspan=1>Contact schedule start time</td></tr><tr><td rowspan=1 colspan=1>Contact_Schedule_Stop_Time</td><td rowspan=1 colspan=1>Contact schedule stop time 0</td></tr><tr><td rowspan=5 colspan=1>IDP_Acct</td><td rowspan=1 colspan=1>*Sub_Intv_Sequence_Id</td><td rowspan=1 colspan=1>Subinterval sequence identification - Asurrogate key for subinterval</td></tr><tr><td rowspan=1 colspan=1>*File_Name</td><td rowspan=1 colspan=1>Band file or browse file name</td></tr><tr><td rowspan=1 colspan=1>Bands_Present</td><td rowspan=1 colspan=1>Bands present (multi -valued)</td></tr><tr><td rowspan=1 colspan=1>File_Type</td><td rowspan=1 colspan=1>Band, mono or multiband browse</td></tr><tr><td rowspan=1 colspan=1>CCA_Method</td><td rowspan=1 colspan=1>CCA method</td></tr><tr><td rowspan=11 colspan=1>LDT_Output_File_Inf0</td><td rowspan=1 colspan=1>*LPS_Hardware_String_Id</td><td rowspan=1 colspan=1>LPS hardware string id</td></tr><tr><td rowspan=1 colspan=1>*LGS_Channel_Id</td><td rowspan=1 colspan=1>Contact channel id</td></tr><tr><td rowspan=1 colspan=1>*Contact_Start_Time</td><td rowspan=1 colspan=1>Contact start time</td></tr><tr><td rowspan=1 colspan=1>*Contact_Stop_Time</td><td rowspan=1 colspan=1>Contact end time</td></tr><tr><td rowspan=1 colspan=1>DAN_Suspended</td><td rowspan=1 colspan=1>Indicator of DAN transfer suspension</td></tr><tr><td rowspan=1 colspan=1>Marked_For_Retention</td><td rowspan=1 colspan=1>Flag indicating deletion of files by LPS</td></tr><tr><td rowspan=1 colspan=1>Time_Available</td><td rowspan=1 colspan=1>Output file for transfer available time</td></tr><tr><td rowspan=1 colspan=1>Time_Deleted</td><td rowspan=1 colspan=1>Output file deletion time</td></tr><tr><td rowspan=1 colspan=1>DAN_Transmission_Time</td><td rowspan=1 colspan=1>DAN transmission time from LPS to DAAC</td></tr><tr><td rowspan=1 colspan=1>DTA_Time_Of_Receipt</td><td rowspan=1 colspan=1>DTA from LP DAAC receipt time by LPS</td></tr><tr><td rowspan=1 colspan=1>Contact_File_Names</td><td rowspan=1 colspan=1>File   names   associated   with  eachsubinterval (multi -valued)</td></tr><tr><td rowspan=5 colspan=1>LPS_Configuration</td><td rowspan=1 colspan=1>*LPS_Hardware_String_Id</td><td rowspan=1 colspan=1>LPS hardware string ID</td></tr><tr><td rowspan=1 colspan=1>LGS_Channel_Id</td><td rowspan=1 colspan=1>LGS channel identification</td></tr><tr><td rowspan=1 colspan=1>Spacecraft_Id</td><td rowspan=1 colspan=1>Landsat 7 spacecraft ID</td></tr><tr><td rowspan=1 colspan=1>Instrument_Id</td><td rowspan=1 colspan=1>Instrument ID (ETM+)</td></tr><tr><td rowspan=1 colspan=1>LPS_Software_Version_Number</td><td rowspan=1 colspan=1>LPS software version number</td></tr></table>

Table 5.2 LPS Logical Schema Definitions (2 of 8)
<table><tr><td colspan="1" rowspan="1">Schema Name</td><td colspan="1" rowspan="1">Attribute Name</td><td colspan="1" rowspan="1">Attribute Description</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">File_Version_Number</td><td colspan="1" rowspan="1">Metadata file version no of a subinterval</td></tr><tr><td colspan="1" rowspan="16">MFP_Acct</td><td colspan="1" rowspan="1">*Sub_Intv_Sequence_Id #</td><td colspan="1" rowspan="1">Subinterval sequence identification - Asurrogate key for subinterval</td></tr><tr><td colspan="1" rowspan="1">Mjf_CADU_Rcvd_Cnt</td><td colspan="1" rowspan="1">Count of received major frame CADUs</td></tr><tr><td colspan="1" rowspan="1">Mjf_CADU_Fly_Cnt</td><td colspan="1" rowspan="1">Count of flywheel major frame CADUs</td></tr><tr><td colspan="1" rowspan="1">Mjf_CADU_Polarity</td><td colspan="1" rowspan="1">CADU sync info polarity of accumul. mjf(multi -valued)</td></tr><tr><td colspan="1" rowspan="1">CADU_Search_Tolerance</td><td colspan="1" rowspan="1">Search tolerance parameters</td></tr><tr><td colspan="1" rowspan="1">CADU_Check_Tolerance</td><td colspan="1" rowspan="1">Check tolerance parameter</td></tr><tr><td colspan="1" rowspan="1">CADU_Flywheel_Tolerance</td><td colspan="1" rowspan="1">Flywheel tolerance parameter</td></tr><tr><td colspan="1" rowspan="1">CADU_Sync_Marker_Check_Error_Tolerance</td><td colspan="1" rowspan="1">Check error tolerance parameter</td></tr><tr><td colspan="1" rowspan="1">CADU_Sync_Lock_Error_Tolerance</td><td colspan="1" rowspan="1">Lock error tolerance parameter</td></tr><tr><td colspan="1" rowspan="1">CADU_Bit_Slip_Correction_Extent</td><td colspan="1" rowspan="1">Slip correction extent parameter</td></tr><tr><td colspan="1" rowspan="1">Mjf_CADU_Bit_Slip</td><td colspan="1" rowspan="1">Bit slip total for accum. major frame set(multi -valued)</td></tr><tr><td colspan="1" rowspan="1">Mjf_CADU_Sync_Err_Cnt</td><td colspan="1" rowspan="1">Count of major frame CADUs withsynchronization errors</td></tr><tr><td colspan="1" rowspan="1">Mjf_CADU_Missing_Cnt</td><td colspan="1" rowspan="1">Number of missing CADUs per major frame</td></tr><tr><td colspan="1" rowspan="1">Mjf_CADU_RS_Corr_Cnt</td><td colspan="1" rowspan="1">Number of correctable VCDU headers permajor frame</td></tr><tr><td colspan="1" rowspan="1">Mjf_CADU_RS_Uncorr_Cnt</td><td colspan="1" rowspan="1">Number of uncorrectable VCDU header permjf</td></tr><tr><td colspan="1" rowspan="1">Mjf_CADU_BCH_Corr_Cnt</td><td colspan="1" rowspan="1">No of CADUs with BCH error corrected inthe mission data zone per major frame</td></tr><tr><td colspan="1" rowspan="2"></td><td colspan="1" rowspan="1">Mjf_CADU_BCH_Uncorr_CNnt</td><td colspan="1" rowspan="1">o of CADUs with BCH error uncorrectedin the mission data zone per major frame</td></tr><tr><td colspan="1" rowspan="1">Mjf_CADU_BCH_Bits_Corr</td><td colspan="1" rowspan="1">Total no of bits of BCH corrected in themission data zone of a CADU</td></tr></table>

Table 5.2 LPS Logical Schema Definitions (3 of 8)
<table><tr><td colspan="1" rowspan="1">Schema Name</td><td colspan="1" rowspan="1">Attribute Name</td><td colspan="1" rowspan="1">Attribute Description</td></tr><tr><td colspan="1" rowspan="13"></td><td colspan="1" rowspan="1">Mjf_CADU_CRC_Err_Cnt</td><td colspan="1" rowspan="1">Count of CADUs with CRC errors</td></tr><tr><td colspan="1" rowspan="1">Mjf_CADU_BER_Cnt</td><td colspan="1" rowspan="1">BER in mission data zone on a subint basis</td></tr><tr><td colspan="1" rowspan="1">Mjf_CADU_Seq_Err_Cnt</td><td colspan="1" rowspan="1">No of VCDU counter errors in a maj. frame</td></tr><tr><td colspan="1" rowspan="1">ETM_Data_Format</td><td colspan="1" rowspan="1">ETM + data format type provided by MFPSand is included in the metadata file</td></tr><tr><td colspan="1" rowspan="1">Mjf_Count</td><td colspan="1" rowspan="1">Count of major frames in subinterval</td></tr><tr><td colspan="1" rowspan="1">Mjf_Tossed_Cnt</td><td colspan="1" rowspan="1">No of mjf calculated from sync errors andend of line code errors on a subint basis</td></tr><tr><td colspan="1" rowspan="1">Mjf_Eol_Err_Cnt</td><td colspan="1" rowspan="1">No of end of line errors on a subint basis</td></tr><tr><td colspan="1" rowspan="1">Mnf_Ctr_Err</td><td colspan="1" rowspan="1">No of minor frame counter errors</td></tr><tr><td colspan="1" rowspan="1">Mjf_Time_Code_Err_Cnt</td><td colspan="1" rowspan="1">Count of imagery time code errors</td></tr><tr><td colspan="1" rowspan="1">Mjf_Full_Fill_Cnt</td><td colspan="1" rowspan="1">Count of entirely filled ETM+ major frames</td></tr><tr><td colspan="1" rowspan="1">Mjf_Part_Fill_Cnt</td><td colspan="1" rowspan="1">Count of partially filled ETM+ majorframes</td></tr><tr><td colspan="1" rowspan="1">Cal_File_Name</td><td colspan="1" rowspan="1">Calibration data file name</td></tr><tr><td colspan="1" rowspan="1">MSCD_File_Name</td><td colspan="1" rowspan="1">Mirror Scan Correction Data file name</td></tr><tr><td colspan="1" rowspan="6">PCD_Acct</td><td colspan="1" rowspan="1">*Sub_Intv_Sequence_Id</td><td colspan="1" rowspan="1">Subinterval sequence identification - Asurrogate key for subinterval</td></tr><tr><td colspan="1" rowspan="1">Orbit_Number</td><td colspan="1" rowspan="1">Orbit number</td></tr><tr><td colspan="1" rowspan="1">Num_PCD_MJF</td><td colspan="1" rowspan="1">Number of PCD major frames</td></tr><tr><td colspan="1" rowspan="1">First_PCD_MJF_Time</td><td colspan="1" rowspan="1">First PCD major frame time</td></tr><tr><td colspan="1" rowspan="1">[PCD_File_Id</td><td colspan="1" rowspan="1">PCD file name</td></tr><tr><td colspan="1" rowspan="1">Failed_PCD_Votes</td><td colspan="1" rowspan="1">Number of failed PCD votes</td></tr><tr><td colspan="1" rowspan="2"></td><td colspan="1" rowspan="1">Num_PCD_MNF_Sync_Errors</td><td colspan="1" rowspan="1">Number of PCD minor frames with syncerrors</td></tr><tr><td colspan="1" rowspan="1">Num_PCD_Filled_MNF</td><td colspan="1" rowspan="1">Number of PCD filled minor frames</td></tr><tr><td colspan="1" rowspan="5"></td><td colspan="1" rowspan="1">Num_PCD_Filled_MJF</td><td colspan="1" rowspan="1">Number of PCD filled major frames</td></tr><tr><td colspan="1" rowspan="1">Num_Avail_ADP</td><td colspan="1" rowspan="1">Number of data points</td></tr><tr><td colspan="1" rowspan="1">Num_Rejected_ADP</td><td colspan="1" rowspan="1">Number of data points rejected</td></tr><tr><td colspan="1" rowspan="1">Num_Missing_ADP</td><td colspan="1" rowspan="1">Number of data point missing</td></tr><tr><td colspan="1" rowspan="1">Num_Avail_EDP</td><td colspan="1" rowspan="1">Number of data points</td></tr></table>

Table 5.2 LPS Logical Schema Definitions (4 of 8)
<table><tr><td rowspan=1 colspan=1>Schema Name</td><td rowspan=1 colspan=1>Attribute Name</td><td rowspan=1 colspan=1>Attribute Description</td></tr><tr><td rowspan=2 colspan=1></td><td rowspan=1 colspan=1>Num_Rejected_EDP</td><td rowspan=1 colspan=1>Number of data points rejected</td></tr><tr><td rowspan=1 colspan=1>Num_Missing_EDP</td><td rowspan=1 colspan=1>Number of data point missing</td></tr><tr><td rowspan=5 colspan=1>RDC_Acct</td><td rowspan=1 colspan=1>*LPS_Hardware_String_Id</td><td rowspan=1 colspan=1>LPS hardware string id</td></tr><tr><td rowspan=1 colspan=1>*LGS_Channel_Id</td><td rowspan=1 colspan=1>Contact channel id</td></tr><tr><td rowspan=1 colspan=1>*Contact_Start_Time</td><td rowspan=1 colspan=1>Contact Start Time</td></tr><tr><td rowspan=1 colspan=1>*Contact_Stop_Time</td><td rowspan=1 colspan=1>Contact end time</td></tr><tr><td rowspan=1 colspan=1>Rcv_Dat_Vol_Mbytes</td><td rowspan=1 colspan=1>Received data volume</td></tr><tr><td rowspan=17 colspan=1>RDP_Acct</td><td rowspan=1 colspan=1>LPS_Hardware_String_Id</td><td rowspan=1 colspan=1>LPS hardware string id</td></tr><tr><td rowspan=1 colspan=1>LGS_Channel_Id</td><td rowspan=1 colspan=1>Contact channel id</td></tr><tr><td rowspan=1 colspan=1>Contact_Start_Time</td><td rowspan=1 colspan=1>Contact start time</td></tr><tr><td rowspan=1 colspan=1>Contact_Stop_Time</td><td rowspan=1 colspan=1>Contact end time</td></tr><tr><td rowspan=1 colspan=1>CADU_Search_Tolerance</td><td rowspan=1 colspan=1>Search tolerance parameter</td></tr><tr><td rowspan=1 colspan=1>CADU_Check_Tolerance</td><td rowspan=1 colspan=1>Check tolerance parameter</td></tr><tr><td rowspan=1 colspan=1>CADU_Flywheel_Tolerance</td><td rowspan=1 colspan=1>Flywheel tolerance parameter</td></tr><tr><td rowspan=1 colspan=1>CADU_Sync_Marker_Check_Error_Tolerance</td><td rowspan=1 colspan=1>Check error tolerance parameter</td></tr><tr><td rowspan=1 colspan=1>CADU_Sync_Lock_Error_Tolerance</td><td rowspan=1 colspan=1>Lock error tolerance parameter</td></tr><tr><td rowspan=1 colspan=1>CADU_Bit_Slip_Correction_Extent</td><td rowspan=1 colspan=1>Slip correction extent parameter</td></tr><tr><td rowspan=1 colspan=1>CADU_Polarity</td><td rowspan=1 colspan=1>CADU polarity (multi -valued)</td></tr><tr><td rowspan=1 colspan=1>CADU_Bit_Slip</td><td rowspan=1 colspan=1>Bit slip total for CADU (multi -valued)</td></tr><tr><td rowspan=1 colspan=1>CADU_Sync_Error_Count</td><td rowspan=1 colspan=1>Count of CADUs with synchronizationerrors</td></tr><tr><td rowspan=1 colspan=1>CADU_Rcv_Count</td><td rowspan=1 colspan=1>Count of received CADUs</td></tr><tr><td rowspan=1 colspan=1>CADU_Flywheel_Count</td><td rowspan=1 colspan=1>Count of flywheel CADUs</td></tr><tr><td rowspan=1 colspan=1>CADU_Missing_Count</td><td rowspan=1 colspan=1>Count of missing CADUs</td></tr><tr><td rowspan=1 colspan=1>CADU_CRC_Error_Count</td><td rowspan=1 colspan=1>CRC errors encountered when CCSDS wasprocessing a raw wideband data set</td></tr></table>

Table 5.2 LPS Logical Schema Definitions (5 of 8)
<table><tr><td rowspan=1 colspan=1>Schema Name</td><td rowspan=1 colspan=1>Attribute Name</td><td rowspan=1 colspan=1>Attribute Description</td></tr><tr><td rowspan=7 colspan=1></td><td rowspan=1 colspan=1>VCDU_Header_Correctable_Error_Count</td><td rowspan=1 colspan=1>Count of correctable VCDU headers, byVCDU-ID (Reed Solomon checked)</td></tr><tr><td rowspan=1 colspan=1>VCDU_Header_Uncor-rectable_Error_Count</td><td rowspan=1 colspan=1>Count of uncorrectable VCDU headers(Reed Solomon checked)</td></tr><tr><td rowspan=1 colspan=1>BCH_Data_Corrected_Error_Count</td><td rowspan=1 colspan=1>Count of CADUs with BCH errors correctedfor the mission data zone in the VCDU</td></tr><tr><td rowspan=1 colspan=1>BCH_Data_Uncorrected_Error_Count</td><td rowspan=1 colspan=1>Count of CADUswithBCHerrorsuncorrected for the mission data zone inthe VCDU</td></tr><tr><td rowspan=1 colspan=1>BCH_Pointer_Corrected_Error_Count</td><td rowspan=1 colspan=1>No of correctable BCH pointer field errorsencountered when CCSDS was processing araw wideband data set</td></tr><tr><td rowspan=1 colspan=1>BCH_Pointer_UncorrectedError_Count</td><td rowspan=1 colspan=1> No of uncorrectable BCH pointer fielderrors encountered when CCSDS wasprocessing a raw wideband data set</td></tr><tr><td rowspan=1 colspan=1>BER</td><td rowspan=1 colspan=1>Bit error rate</td></tr><tr><td rowspan=8 colspan=1>Sub_Intv</td><td rowspan=1 colspan=1>*LPS_Hardware_String_Id</td><td rowspan=1 colspan=1>LPS hardware string id</td></tr><tr><td rowspan=1 colspan=1>*LGS_Channel_Id</td><td rowspan=1 colspan=1>Contact channel id</td></tr><tr><td rowspan=1 colspan=1>*Contact_Start_Time</td><td rowspan=1 colspan=1>Contact start time</td></tr><tr><td rowspan=1 colspan=1>*Contact_Stop_Time</td><td rowspan=1 colspan=1>Contact end time</td></tr><tr><td rowspan=1 colspan=1>*Sub_Intv_Sequence_Id</td><td rowspan=1 colspan=1>Subinterval sequence identification - Asurrogate key for subinterval</td></tr><tr><td rowspan=1 colspan=1>MF_Start_Time</td><td rowspan=1 colspan=1>Subinterval start time</td></tr><tr><td rowspan=1 colspan=1>MF_Stop_Time</td><td rowspan=1 colspan=1>Subinterval stop time</td></tr><tr><td rowspan=1 colspan=1>VCID</td><td rowspan=1 colspan=1>Virtual channel identification</td></tr><tr><td rowspan=5 colspan=1>Valid_Band_Parms</td><td rowspan=1 colspan=1>Mono</td><td rowspan=1 colspan=1>Monochrome browse band</td></tr><tr><td rowspan=1 colspan=1>Multi1</td><td rowspan=1 colspan=1>Multiband browse band</td></tr><tr><td rowspan=1 colspan=1>Multi2</td><td rowspan=1 colspan=1>Multiband browse band</td></tr><tr><td rowspan=1 colspan=1>Multi3</td><td rowspan=1 colspan=1>Multiband browse band</td></tr><tr><td rowspan=1 colspan=1>Subs</td><td rowspan=1 colspan=1>Subsampling reduction ratios</td></tr></table>

Table 5.2 LPS Logical Schema Definitions (6 of 8)
<table><tr><td rowspan=1 colspan=1>Schema Name</td><td rowspan=1 colspan=1>Attribute Name</td><td rowspan=1 colspan=1>Attribute Description</td></tr><tr><td rowspan=3 colspan=1></td><td rowspan=1 colspan=1>Wave</td><td rowspan=1 colspan=1>Wavelet reduction ratios</td></tr><tr><td rowspan=1 colspan=1>CCA_Method</td><td rowspan=1 colspan=1>CCA method</td></tr><tr><td rowspan=1 colspan=1>CCA_Ratio</td><td rowspan=1 colspan=1>CCA ratio</td></tr><tr><td rowspan=6 colspan=1>Valid_CCSDS_Parms</td><td rowspan=1 colspan=1>CADU_Search_Tolerance</td><td rowspan=1 colspan=1>Search tolerance parameter</td></tr><tr><td rowspan=1 colspan=1>CADU_Check_Tolerance</td><td rowspan=1 colspan=1>Check tolerance parameter</td></tr><tr><td rowspan=1 colspan=1>CADU_Flywheel_Tolerance</td><td rowspan=1 colspan=1>Flywheel tolerance parameter</td></tr><tr><td rowspan=1 colspan=1>CADU_Sync_Marker_Check_Error_Tolerance</td><td rowspan=1 colspan=1>Check error tolerance parameter</td></tr><tr><td rowspan=1 colspan=1>CADU_Sync_Lock_Error_Tolerance</td><td rowspan=1 colspan=1>Lock error tolerance parameter</td></tr><tr><td rowspan=1 colspan=1>CADU_Bit_Slip_Correction_Extent</td><td rowspan=1 colspan=1>Slip correction extent parameter</td></tr><tr><td rowspan=8 colspan=1>Valid_MFP_Parms</td><td rowspan=1 colspan=1>Sensor_Alignment_Info</td><td rowspan=1 colspan=1>Information to perform integer-pixelalignment (multi -valued)</td></tr><tr><td rowspan=1 colspan=1>Fill_Value</td><td rowspan=1 colspan=1>Fill value for major frame processing</td></tr><tr><td rowspan=1 colspan=1>Sub_Intv_Delta</td><td rowspan=1 colspan=1>Delta for determining subinterval</td></tr><tr><td rowspan=1 colspan=1>Mjf_Data_Rate</td><td rowspan=1 colspan=1>Data rate threshold</td></tr><tr><td rowspan=1 colspan=1>Max_Alignment_Value</td><td rowspan=1 colspan=1>Maximum alignment value</td></tr><tr><td rowspan=1 colspan=1>Time_Range_Tol</td><td rowspan=1 colspan=1>Time range tolerance</td></tr><tr><td rowspan=1 colspan=1>Part_Mnf_Tol</td><td rowspan=1 colspan=1>Minor frame tolerance</td></tr><tr><td rowspan=1 colspan=1>Maj_Vote_Tol</td><td rowspan=1 colspan=1>Majority voting tolerance</td></tr><tr><td rowspan=5 colspan=1>Valid_MFP_Thres</td><td rowspan=1 colspan=1>Mjf_CADU_Seq_Err_Thr</td><td rowspan=1 colspan=1>Threshold value for the number ofsequence counter errors</td></tr><tr><td rowspan=1 colspan=1>Scan_Dir_Thr</td><td rowspan=1 colspan=1>The counter thresholds for the VCDUidentification process</td></tr><tr><td rowspan=1 colspan=1>Sync_Thr</td><td rowspan=1 colspan=1>The maximum number of sync errorallowed</td></tr><tr><td rowspan=1 colspan=1>Mnf_Ctr_Thr</td><td rowspan=1 colspan=1>The maximum number of minor frameerrors allowed</td></tr><tr><td rowspan=1 colspan=1>Eol_Thr</td><td rowspan=1 colspan=1>The maximum number of end of line errorallowed</td></tr></table>

Table 5.2 LPS Logical Schema Definitions (7 of 8)
<table><tr><td colspan="1" rowspan="1">Schema Name</td><td colspan="1" rowspan="1">Attribute Name</td><td colspan="1" rowspan="1">Attribute Description</td></tr><tr><td colspan="1" rowspan="3"></td><td colspan="1" rowspan="1">Tc_Thr</td><td colspan="1" rowspan="1">The maximum number of time code errorallowed</td></tr><tr><td colspan="1" rowspan="1">Full_Mjf_Thr</td><td colspan="1" rowspan="1">The maximum number of full filled majorframe allowed</td></tr><tr><td colspan="1" rowspan="1">Part_Mjf_Thr</td><td colspan="1" rowspan="1">The maximum number of partial filledmajor frame allowed</td></tr><tr><td colspan="1" rowspan="1">Valid_PCD_Parms</td><td colspan="1" rowspan="1">PCD_Frame_Fill_Value</td><td colspan="1" rowspan="1">Predefined value that is used to fillmissing PCD data when building PCDminor and major frames</td></tr><tr><td colspan="1" rowspan="8">Valid_PCD_Thres</td><td colspan="1" rowspan="1">Ephem_Position_Upper</td><td colspan="1" rowspan="1">Largest valid ephemeris position data pnt</td></tr><tr><td colspan="1" rowspan="1">Ephem_Position_Lower</td><td colspan="1" rowspan="1">Smallest valid ephemeris position data pnt</td></tr><tr><td colspan="1" rowspan="1">Ephem_Velocity_Upper</td><td colspan="1" rowspan="1">Largest valid ephemeris data point</td></tr><tr><td colspan="1" rowspan="1">Ephem_Velocity_Lower</td><td colspan="1" rowspan="1">Smallest valid ephemeris data point</td></tr><tr><td colspan="1" rowspan="1">Att_Lower_Bounds</td><td colspan="1" rowspan="1">Lowest valid value of any attitudecomponent</td></tr><tr><td colspan="1" rowspan="1">Att_Upper_Bounds</td><td colspan="1" rowspan="1">Highest valid value of any attitudecomponent</td></tr><tr><td colspan="1" rowspan="1">Num_Missing_Data_Words</td><td colspan="1" rowspan="1">The threshold for reporting errors whenPCD information words are missing</td></tr><tr><td colspan="1" rowspan="1">Num_Failed_Votes</td><td colspan="1" rowspan="1">The threshold for reporting errors whenunsuccessful majority votes are performed</td></tr><tr><td colspan="1" rowspan="4">Valid_RDP_Thres</td><td colspan="1" rowspan="1">Sync_Thres</td><td colspan="1" rowspan="1">Max no of sync errors allowed beforenotifying the operator</td></tr><tr><td colspan="1" rowspan="1">CRC_Thres</td><td colspan="1" rowspan="1">Max no of CRC errors allowed beforenotifying the operator</td></tr><tr><td colspan="1" rowspan="1">RS_Thres</td><td colspan="1" rowspan="1">Max no of Reed Solomon errors allowedbefore notifying the operator</td></tr><tr><td colspan="1" rowspan="1">BCH_Thres</td><td colspan="1" rowspan="1">Max no of BCH errors allowed beforenotifying the operator</td></tr><tr><td></td><td>BER_Thres</td><td>Max no of bit error rate allowed before notifying the operator</td></tr></table>

Table 5.2 LPS Logical Schema Definitions (8 of 8)
<table><tr><td colspan="1" rowspan="1">Schema Name</td><td colspan="1" rowspan="1">Attribute Name</td><td colspan="1" rowspan="1">Attribute Description</td></tr><tr><td colspan="1" rowspan="8">Valid_Scene_Parms</td><td colspan="1" rowspan="1">ETM_Plus_To_Body_TranS</td><td colspan="1" rowspan="1">Parms used to transform the latitude,longitude, sun elevation, and sun azimuthfrom ETM Plus to Spacecraft Body</td></tr><tr><td colspan="1" rowspan="1">Mission_Start_Time</td><td colspan="1" rowspan="1">Start time of the Landsat Mission</td></tr><tr><td colspan="1" rowspan="1">Time_Per_Orbit</td><td colspan="1" rowspan="1">Amount time required for Landsat to makeone complete orbit</td></tr><tr><td colspan="1" rowspan="1">Semi_Major_Axis</td><td colspan="1" rowspan="1">Distance from Apogee or Perigee to thecenter of the orbit ellipse</td></tr><tr><td colspan="1" rowspan="1">Semi_Minor_Axis</td><td colspan="1" rowspan="1">Polar axis radius</td></tr><tr><td colspan="1" rowspan="1">ETM_Plus_LOS_x</td><td colspan="1" rowspan="1">X-coordinate of the line of sight vector</td></tr><tr><td colspan="1" rowspan="1">ETM_Plus_LOS_y</td><td colspan="1" rowspan="1">y-coordinate of the line of sight vector</td></tr><tr><td colspan="1" rowspan="1">ETM_Plus_LOS_z</td><td colspan="1" rowspan="1">Z-coordinate of the line of sight vector</td></tr><tr><td colspan="1" rowspan="11">Valid_WRS_Parms</td><td colspan="1" rowspan="1">*WRS_Path_Nominal</td><td colspan="1" rowspan="1">WRS path number</td></tr><tr><td colspan="1" rowspan="1">*WRS_Row_Nominal</td><td colspan="1" rowspan="1">WRS row number</td></tr><tr><td colspan="1" rowspan="1">Scene_Center_Latitude</td><td colspan="1" rowspan="1">Scene center latitude</td></tr><tr><td colspan="1" rowspan="1">Scene_Center_Longitude</td><td colspan="1" rowspan="1">Scene center longitude</td></tr><tr><td colspan="1" rowspan="1">Upper_Left_Corner_Latitude</td><td colspan="1" rowspan="1">Upper left corner latitude</td></tr><tr><td colspan="1" rowspan="1">Upper_Right_Corner_Latitude</td><td colspan="1" rowspan="1">Upper right corner latitude</td></tr><tr><td colspan="1" rowspan="1">Lower_Left_Corner_Latitude</td><td colspan="1" rowspan="1">Lower left corner latitude</td></tr><tr><td colspan="1" rowspan="1">Lower_Right_Corner_Latitude</td><td colspan="1" rowspan="1">Lower right corner latitude</td></tr><tr><td colspan="1" rowspan="1">Upper_Left_Corner_Longitude</td><td colspan="1" rowspan="1">Upper left corner longitude</td></tr><tr><td colspan="1" rowspan="1">Upper_Right_Corner_Longitude</td><td colspan="1" rowspan="1">Upper right corner longitude</td></tr><tr><td colspan="1" rowspan="1">Lower_Left_Corner_Longitude</td><td colspan="1" rowspan="1">Lower left corner longitude</td></tr><tr><td></td><td>Lower_Right_Corner_ Longitude</td><td>Lower right corner longitude</td></tr></table>

## 5.2.2 Functional Usage Analysis

A preliminary data usage analysis is performed during the logical design process which examines the manner in which the LPS subsystems and processes interact with the database. The functional usage of the database can be presented using interface diagrams and CRUD matrices. Table 5.3 is a CRUD matrix that depicts the interactions between LPS subsystems and database schemata. Convention: I - Insert, U - Update, D - Delete, Q - Query.

Table 5.3 LPS Subsystem CRUD Matrix
<table><tr><td rowspan=1 colspan=1>Schema\Subsystem</td><td rowspan=1 colspan=1>RDCS</td><td rowspan=1 colspan=1>RDPS</td><td rowspan=1 colspan=1>MFPS</td><td rowspan=1 colspan=1>PCDS</td><td rowspan=1 colspan=1>IDPS</td><td rowspan=1 colspan=1>MACS</td><td rowspan=1 colspan=1>LDTS</td></tr><tr><td rowspan=1 colspan=1>Contact_Schedules</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>IDP_Acct</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>LDT_Output_File_Info</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td></tr><tr><td rowspan=1 colspan=1>LPS_Configuration</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>MFP_Acct</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>PCD_Acct</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>RDC_Acct</td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>RDP_Acct</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Sub_Intv</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_Band_Parms</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_CCSDS_Parms</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_MFP_Parms</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_MFP_Thres</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_PCD_Parms</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_PCD_Thres</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_RDP_Thres</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_Scene_Parms</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_WRS_Parms</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td></tr></table>

Figure 5.4 through 5.10 illustrate the interface between major processes in each subsystem and the database. The CRUD matrix for each subsystem is also included in the following figures.
<table><tr><td rowspan=1 colspan=1>Schema\Process</td><td rowspan=1 colspan=1>Receive RawWidebandData</td><td rowspan=1 colspan=1>Restage RawWidebandData</td><td rowspan=1 colspan=1>Generate DataReceiveSummary</td></tr><tr><td rowspan=1 colspan=1>LPS_Configuration</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>RDC_Acct</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>Q</td></tr></table>

![](images/b12428cf3d6e5aaaf4d70e99fcbd9bd2d6eb9b72b53548f02f5b33ee07eef9e6.jpg)  
Figure 5.4 RDCS Database Interface

<table><tr><td rowspan=1 colspan=1>Schema\Process</td><td rowspan=1 colspan=1>ValidateRDPPara-meters</td><td rowspan=1 colspan=1>Synchro-nizeCCSDSFrame</td><td rowspan=1 colspan=1>ProcessCCSDSGrade 3</td><td rowspan=1 colspan=1>DecodeBCH</td><td rowspan=1 colspan=1>ComputelBER</td><td rowspan=1 colspan=1>GenerateReturnLink QAReport</td></tr><tr><td rowspan=1 colspan=1>RDP_Acct</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td></tr><tr><td rowspan=1 colspan=1>Valid_CCSDS_Parms</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_RDP_Thres</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td></tr></table>

![](images/38fbaca7d34a42be4b8f4b63887dfb96b23845b57be18885f8544a4f71e90764.jpg)  
Figure 5.5 RDPS Database Interface

<table><tr><td rowspan=1 colspan=1>Schema\Process</td><td rowspan=1 colspan=1>Vali-dateMFPPara-mets</td><td rowspan=1 colspan=1>Coll-ectVCDUQty &amp;Acct</td><td rowspan=1 colspan=1>Iden-tifyVCDU</td><td rowspan=1 colspan=1>ParseMajorFrme</td><td rowspan=1 colspan=1>Col-lectQlty &amp;Acct</td><td rowspan=1 colspan=1>Gene-rateBandData</td><td rowspan=1 colspan=1>Ext-ractCalibData</td><td rowspan=1 colspan=1>CreateCCalibFile</td><td rowspan=1 colspan=1>reateMSCDFile</td><td rowspan=1 colspan=1>Gene-rateReport</td></tr><tr><td rowspan=1 colspan=1>LPS_Con-figuration</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>MFP_Acct</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>Q</td></tr><tr><td rowspan=1 colspan=1>RDP_Acct</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Sub_Intv</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td></tr><tr><td rowspan=1 colspan=1>Valid_MFPParms</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_MFPThres</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr></table>

![](images/658629e66ec7f565efe3482cb094361072f0382e0aae35cb7477252a57a83abf.jpg)  
Figure 5.6  
MFPS Data Interface

<table><tr><td rowspan=1 colspan=1>Schema\Process</td><td rowspan=1 colspan=1>ValidatePCDParameters</td><td rowspan=1 colspan=1>AssemblePCDCycles</td><td rowspan=1 colspan=1>CalculateSceneInfo</td><td rowspan=1 colspan=1>CreatePCD File</td></tr><tr><td rowspan=1 colspan=1>LPS_Configuration</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td></tr><tr><td rowspan=1 colspan=1>PCD_Acct</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>I,U</td></tr><tr><td rowspan=1 colspan=1>Sub_Intv</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td></tr><tr><td rowspan=1 colspan=1>Valid_PCD_Parms</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_PCD_Thres</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_Scene_Parms</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td></tr><tr><td rowspan=1 colspan=1>Valid_WRS_Parms</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td></tr></table>

![](images/d10458419512a83137f712c44d313d2eb4ea620e82c2d38adfc5978c26ac69e8.jpg)  
Figure 5.7  
PCDS Database Interface

Figure 5.8 IDPS Database Interface
<table><tr><td rowspan=1 colspan=1>Schema\Process</td><td rowspan=1 colspan=1>Validate BandParameter</td><td rowspan=1 colspan=1>GenerateBrowse File</td><td rowspan=1 colspan=1>GenerateBand File</td><td rowspan=1 colspan=1>PerformACCA</td></tr><tr><td rowspan=1 colspan=1>IDP_Acct</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>I,U</td></tr><tr><td rowspan=1 colspan=1>LPS_Configuration</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Sub_Intv</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Valid_Band_Parms</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td></tr></table>

![](images/f1efdd62a9d6967102bf4a8fd7dfb9e25223d4df50f4f71978979ec9b5be783f.jpg)

<table><tr><td rowspan=1 colspan=1>Schema\Process</td><td rowspan=1 colspan=1>Modify LPSConfiguration</td><td rowspan=1 colspan=1>Modify ContactSchedule</td><td rowspan=1 colspan=1>GenerateMetadata</td></tr><tr><td rowspan=1 colspan=1>Contact_Schedules</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>IDP_Acct</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td></tr><tr><td rowspan=1 colspan=1>LPS_Configuration</td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td></tr><tr><td rowspan=1 colspan=1>MFP_Acct</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td></tr><tr><td rowspan=1 colspan=1>PCD_Acct</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td></tr><tr><td rowspan=1 colspan=1>Sub_Intv</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td></tr><tr><td rowspan=1 colspan=1>Valid_WRS_Parms</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Q</td></tr></table>

![](images/c58d51b008f930f2492bde9d43bd67b9722bb8af68844e10089f05c66ffa876a.jpg)  
Figure 5.9  
MACS Database Interface

<table><tr><td rowspan=1 colspan=1>Schema\Process</td><td rowspan=1 colspan=1>GeneratelDAN</td><td rowspan=1 colspan=1>SendDAN</td><td rowspan=1 colspan=1>ControlSendDAN</td><td rowspan=1 colspan=1>DeleteLPSFiles</td><td rowspan=1 colspan=1>RetainLPSFiles</td><td rowspan=1 colspan=1>ReceiveDTA</td><td rowspan=1 colspan=1>GenerateTransferSummary</td></tr><tr><td rowspan=1 colspan=1>LDT_Output_File_Info</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1>Q</td><td rowspan=1 colspan=1>I,U,Q</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>I,U</td><td rowspan=1 colspan=1>Q</td></tr></table>

![](images/f438431222c4ed97450cf11d43a0f9ff36edc1f2f6c7621d03ecc83beb862012.jpg)  
Figure 5.10 LDTS Database Interface

## 6.0 User Interface (UI)

The LPS user interface consists of all elements of interaction between LPS and the operator. For LPS, this interaction will probably be some combination of system level commands and Oracle user interface products. There is the possibility that existing products, such as a process manager ('DPCP' described in section 6.3.2 Reusability ), will be used.

Concurrent development of the software requirements and the user interface offers specific advantages. By examining the interactions expected between the operators and the system, we can avoid potential problems and aid the understanding of what the subsystems must do in order to perform their function. Another important benefit to beginning work on the user interface is that software drivers may be uncovered by close inspection of how the system will be required to operate. Finally, early effort can lead to a preliminary user interface, offering the chance for users to provide input into the design decisions of both the final user interface and the application software.

Preliminary analysis in the user interface area has covered the areas of task analysis, performance goal setting, and user interface mockup. The results of these studies are presented in the next three sections.

## 6.1 Task Analysis

The task analysis provides a conceptual framework from which to approach the design of the user interface. It explains drivers and limitations on what the user interface will or will not be.

## 6.1.1 Drivers

w The operator is required to setup, test, monitor, and control the LPS system.

w Each LPS string is physically and logically independent. Each string must have its own user interface.

w Operations can be performed on several contacts at one time. The processing of contact 1 can still be going on while contact 2 needs to be captured.

## 6.1.2 Constraints

w The budget for the user interface is very limited. Many choices will be based on budgetary constraints.

## 6.1.3 Assumptions

w No network interface will be available for input of schedules, parameters, etc. between LPS and external systems.

w No security will be provided other than what is available from the UNIX shell and from ORACLE.

w There will be only one type of user for the LPS system. This user type is classified as an "operator".

w The LPS operators will be capable of utilizing the operating system to perform some of the user interface functions. No elaborate shell program is needed to buffer the operator from UNIX.

w No long term or trend reporting is required.

## 6.1.4 Decisions

w The user interface will be developed as some combination of UNIX shell commands, ORACLE SQL-MENUS, and ORACLE SQL-FORMS. It is possible that some COTS or reusable code may be identified and used.

w There will be no automated coordination between strings. This implies that there will be no system wide reporting.

w Prototype user interface screens will be developed and reviewed by LPS operators.

## 6.1.5 User Interface Event List

This section contains a complete list of all known interactions between the LPS system and the operator.

## SYSTEM CONFIGURATION

<table><tr><td>F&amp;PS</td><td>EVENT</td><td>SUBSYSTEM</td><td>Data Dictionary</td></tr><tr><td>3.1.14</td><td>Configure LPS (normal/fall back)</td><td>System Level</td><td>None</td></tr></table>

## THRESHOLDS

<table><tr><td>F&amp;PS</td><td>EVENT</td><td>SUBSYSTEM</td><td>Data Dictionary</td></tr><tr><td>3.3.6.6</td><td>Input RDPS Thresholds</td><td>RDPS</td><td>RDP_Thresholds</td></tr><tr><td>3.3.6.6</td><td>Input MFPS Thresholds</td><td>MFPS</td><td>MFP_Thresholds</td></tr><tr><td>3.3.6.6</td><td>Input PCDS Thresholds</td><td>PCDS</td><td>PCD_Thresholds</td></tr></table>

## PARAMETERS

<table><tr><td>F&amp;PS</td><td>EVENT</td><td>SUBSYSTEM</td><td>Data Dictionary</td></tr><tr><td>3.3.6.1</td><td>Input LPS configuration</td><td>MACS</td><td>LPS_Configuration</td></tr><tr><td>3.2.1</td><td>Input contact schedules (from LGS)</td><td>MACS</td><td>Contact_Schedules</td></tr><tr><td>derived</td><td>Input MFP Parameters</td><td>MFPS</td><td>MFP_Parms</td></tr><tr><td>3.3.2.22</td><td>Input sensor align.tables (from IAS)</td><td>MFPS</td><td>Sensor_Alignment_Info</td></tr><tr><td>3.3.2.1</td><td>Input CCSDS AOS grade 3 parameters</td><td>RDPS</td><td>RDP_CCSDS_Parms</td></tr><tr><td>3.3.3.2</td><td>Input Browse Monochrome Band</td><td>IDPS</td><td>IDP_Band_Parms</td></tr><tr><td>3.3.3.3</td><td>Input Browse Multi Band 1,2&amp;3</td><td>IDPS</td><td>IDP_Band_Parms</td></tr><tr><td>3.3.4.10</td><td>Input ACCA comparison values</td><td>IDPS</td><td>IDP_Band_Parms</td></tr><tr><td>derived</td><td>Input PCD Parameters</td><td>PCDS</td><td>PCD_Parms</td></tr></table>

## TEST

<table><tr><td>F&amp;PS</td><td>EVENT</td><td>SUBSYSTEM</td><td></td><td>Data Dictionary</td></tr><tr><td></td><td>3.1.10.6 Test functions and external interfaces</td><td></td><td>System Level</td><td>None</td></tr><tr><td></td><td>3.1.10.7 Execute diagnostic tests</td><td>System Level None</td><td></td><td></td></tr><tr><td></td><td>3.1.10.8 Support end-to-end testing of LPS functions</td><td></td><td>System Level</td><td>None</td></tr><tr><td>3.1.19</td><td>Read test points to verify proper operation</td><td></td><td>System Level</td><td>None</td></tr></table>

## CONTROL

<table><tr><td>F&amp;PS</td><td>EVENT</td><td>SUBSYSTEM</td><td></td><td>Data Dictionary</td></tr><tr><td>3.1.10.1 Startup LPS</td><td></td><td>IRIX</td><td>None</td><td></td></tr><tr><td>3.1.10.2 Shutdown LPS</td><td></td><td>IRIX</td><td></td><td>None</td></tr><tr><td>3.1.11</td><td>Control LPS operations</td><td></td><td></td><td></td></tr><tr><td>3.3.6.9a</td><td>- Start capture of wideband data</td><td></td><td>RDCS</td><td>RDC_Capture_Drct</td></tr><tr><td>3.3.6.9a</td><td>- Stop capture of wideband data</td><td></td><td>RDCS</td><td>RDC_Capture_Drct</td></tr><tr><td>3.3.1.7</td><td>- Start copy from disk to tape</td><td></td><td>RDCS</td><td>RDC_Save_Drct</td></tr><tr><td>derived</td><td>- Stop copy from disk to tape</td><td>RDCS</td><td></td><td>RDC_Save_Drct</td></tr><tr><td>3.3.1.9</td><td>- Start copy from tape to disk</td><td></td><td>RDCS</td><td>RDC_Restage_Drct</td></tr><tr><td>derived</td><td>- Stop copy from tape to disk</td><td>RDCS</td><td></td><td>RDC_Restage_Drct</td></tr><tr><td>3.3.6.9b</td><td>- Start Level OR Processing</td><td>RDPS</td><td></td><td>RDP_Process_Drct</td></tr><tr><td>3.3.6.9b</td><td>- Stop Level OR Processing</td><td>IRIX kill</td><td>None IRIX kill</td><td>None</td></tr><tr><td>3.3.6.8</td><td colspan="4">Manually override automated functions</td></tr></table>

## MONITORING

<table><tr><td>F&amp;PS</td><td>EVENT</td><td>SUBSYSTEM</td><td>Data Dictionary</td></tr><tr><td>3.1.12</td><td>Monitor LPS operations</td><td>ALL (MACS)</td><td>Assorted error messages</td></tr><tr><td>3.3.6.7</td><td>Report error threshold exceeded</td><td>All</td><td>Assorted error messages</td></tr><tr><td>3.3.6.7</td><td>Report result threshold exceeded</td><td>All</td><td>Assorted error messages</td></tr><tr><td>3.1.10.3</td><td>Report error messages</td><td>ALL (MACS)</td><td>Assorted error messages</td></tr><tr><td>3.1.10.4</td><td>Isolate system faults</td><td>MACS/IRIX</td><td>LPS_Journal</td></tr><tr><td>3.1.10.5</td><td>Recover from system faults</td><td>MACS/IRIX</td><td>LPS_Journal</td></tr><tr><td>derived</td><td>Examine LPS_Journal</td><td>text editor</td><td>LPS_Status</td></tr></table>

## FILE MANAGEMENT

<table><tr><td>F&amp;PS</td><td>EVENT</td><td>SUBSYSTEM</td><td colspan="2">Data Dictionary</td></tr><tr><td>3.3.6.9c</td><td>Enable File Transfer</td><td colspan="2">MACS/LDTS</td><td>LDT_Enable_File_Xfer_Drct</td></tr><tr><td>3.3.6.9c</td><td>Disable File Transfer</td><td>MACS/LDTS</td><td></td><td>LDT_Disable_File_Xfer_Drct</td></tr><tr><td>derived</td><td>Delete Raw Data Input File</td><td>RDCS</td><td>RDC_Delete_Drct</td><td></td></tr><tr><td>3.3.5.5</td><td>Delete output files on contact basis</td><td>LDTS</td><td></td><td>LDT_Delete_Files_Drct</td></tr><tr><td>3.3.5.6</td><td>Retain output files on contact basis</td><td>LDTS</td><td></td><td>LDT_Retain_Files_Drct</td></tr><tr><td>3.3.2.8</td><td>Examine CADU CCSDS trouble files</td><td>IRIX</td><td>n/a</td><td></td></tr><tr><td>3.3.2.10</td><td>Examine CADU BCH trouble files</td><td>text editor</td><td>n/a</td><td></td></tr><tr><td>derived</td><td>Resend DAN to LP DAAC</td><td>LDTS/MACS</td><td>LDT_Resend_DAN_Drct</td><td></td></tr></table>

## REPORTS

<table><tr><td>F&amp;PS</td><td>EVENT SUBSYSTEM</td></tr><tr><td>3.3.1.10.1</td><td>Display wideband data receive summary</td></tr><tr><td>3.3.1.10.1 Print wideband data receive summary RDC_Rpt_Data_Capture_Sum_Drct</td><td></td></tr><tr><td>3.3.6.41</td><td>Display Return link Q&amp;A data (contact) RDPS</td></tr><tr><td>3.3.6.4.1</td><td>Print Return link Q&amp;A data (contact)</td></tr><tr><td></td><td>3.3.6.4 Display level 0R Q&amp;A data (subinterval) MFPS</td></tr><tr><td>3.3.6.4.1</td><td>Print level OR Q&amp;A data (subinterval)</td></tr><tr><td>3.3.6.5.1 Print transfer summary (contact)</td><td>3.3.6.5 Display transfer summary (contact) LDTS LDTS</td></tr></table>

<table><tr><td colspan="2">Data Dictionary</td></tr><tr><td>RDCS</td><td>RDC_Rpt_Data_Capture_Sum_Drct</td></tr><tr><td>RDPS</td><td>RDP_Rpt_Return_Link_QA_Drct RDP_Rpt_Return_Link_QA_D</td></tr><tr><td>MFP_Rpt_LOR_QA_Drct</td><td></td></tr><tr><td>MFPS</td><td>MFP_Rpt_LOR_QA_Drct LDT_Rpt_File_Xfer_Sum_Drct LDT_Rpt_File_Xfer_Sum_Drct</td></tr></table>

## 6.2 User Interface Goals

This section is commonly used to define specific quantitative goals defining minimal acceptable user interface performance. Due to the limited budget of the LPS, it is undesirable to place hard restrictions on items like response time, when a slightly relaxed requirement could produce a user interface at a much lower cost. LPS will seek to develop a user interface which is responsive, easy to use, and maximizes efficient operations.

## 6.3 User Interface Mock-up

The user interface consists of three different types of commands - Operating System, reusable COTS software, and ORACLE SQL-MENU and SQL-FORMS.

## 6.3.1 Operating System

UNIX commands will be used to start the LPS system on each string.

The UNIX "tar" command can satisfy the need to start and stop the copy to short term storage.

The operating system will be used to set the priority of LPS processes.

## 6.3.2 Reusability

If applicable and practical, pre-existing software will be used for the LPS user interface. These reuse sources have already been described in section 3.

One possible source of such software is NASA's Ground Operations Technology Testbed (Code 520 ).

w The first possible reuse item identified is the Distributed Process Control Program (DPCP). This tool enables an operator to start and monitor a set of processes running on one or more host computers.

w The second possible reuse tool is the Distributed Application Monitor Tool (DAMT). This tool may help to analyze the performance of the system.

Another possible source of reuse is the Centralized Information System (CIS) of the Spacelab Data Processing Facility (SLDPF).

## 6.3.3 Oracle Screens

Oracle SQL-MENUS will be used to create a simple menu based user interface. This section presents a possible menu configuration. The purpose of these examples is to demonstrate the types of operations that can be performed via the user interface. These examples do not necessarily represent the actual look and feel of the LPS user interface. User interface screens and menus will be prototyped and reviewed with EDC operations personnel during the preliminary design phase.

## 6.3.3.1 Main Menu

<table><tr><td rowspan=1 colspan=1>EXIT</td><td rowspan=1 colspan=1>SETUP</td><td rowspan=1 colspan=1>TEST</td><td rowspan=1 colspan=1>CONTROL</td><td rowspan=1 colspan=1>MONITOR</td><td rowspan=1 colspan=1>FILES</td><td rowspan=1 colspan=1>REPORTS</td></tr></table>

## 6.3.3.2 Setup Menu

<table><tr><td rowspan=1 colspan=1>EXIT</td><td rowspan=1 colspan=1>SETUP</td><td rowspan=1 colspan=1>TEST</td><td rowspan=1 colspan=1>CONTROL</td><td rowspan=1 colspan=1>MONITOR</td><td rowspan=1 colspan=2>FILES</td><td rowspan=1 colspan=1>REPORTS</td></tr><tr><td rowspan=2 colspan=1></td><td rowspan=1 colspan=5>LPS String Configuration ..Thresholds &amp; Parameters</td><td rowspan=2 colspan=2></td></tr><tr><td rowspan=1 colspan=5>Modify Contact Schedule </td><td rowspan=1 colspan=1></td></tr></table>

## 6.3.3.3 Thresholds and Parameters Menu

<table><tr><td rowspan=1 colspan=1>EXIT</td><td rowspan=1 colspan=1>SETUP</td><td rowspan=1 colspan=1>TEST</td><td rowspan=1 colspan=1>CONTROL</td><td rowspan=1 colspan=1>MONITOR</td><td rowspan=1 colspan=2>FILES</td><td rowspan=2 colspan=1>REPORTS</td></tr><tr><td rowspan=5 colspan=6></td><td rowspan=1 colspan=2>LPS String Configuration ...</td></tr><tr><td rowspan=1 colspan=5>Thresholds & Parameters</td><td rowspan=1 colspan=2>Raw Data Processing ...</td></tr><tr><td rowspan=1 colspan=5>Modify Contact Schedule...</td><td rowspan=1 colspan=2>Major Frame Processing ..</td></tr><tr><td rowspan=1 colspan=5>Modify Sensor Alignment Tables ...</td><td rowspan=1 colspan=2>Payload Correction Data ...</td></tr><tr><td rowspan=1 colspan=2>Image Processing ..</td></tr></table>

6.3.3.4 Test Menu
<table><tr><td rowspan=1 colspan=1>EXIT</td><td rowspan=1 colspan=1>SETUP</td><td rowspan=1 colspan=1>TEST</td><td rowspan=1 colspan=1>CONTROL</td><td rowspan=1 colspan=1>MONITOR</td><td rowspan=1 colspan=1>FILES</td><td rowspan=1 colspan=1>REPORTS</td></tr><tr><td rowspan=1 colspan=2></td><td rowspan=1 colspan=4>TBD</td><td rowspan=1 colspan=1></td></tr></table>

## 6.3.3.5 Control Menu

<table><tr><td rowspan=1 colspan=1>EXIT</td><td rowspan=1 colspan=1>SETUP</td><td rowspan=1 colspan=1>TEST</td><td rowspan=1 colspan=1>CONTROL</td><td rowspan=1 colspan=1>MONITOR</td><td rowspan=1 colspan=1>FILES</td><td rowspan=1 colspan=1>REPORTS</td></tr><tr><td rowspan=8 colspan=3></td><td rowspan=1 colspan=4>Start Capture ...</td></tr><tr><td rowspan=1 colspan=4>Stop Capture ...</td></tr><tr><td rowspan=1 colspan=4>Start Copy to Tape ...</td></tr><tr><td rowspan=1 colspan=4>Stop Copy to Tape ...</td></tr><tr><td rowspan=1 colspan=4>Start Copy from Tape ...</td></tr><tr><td rowspan=1 colspan=4>Stop Copy from Tape ..</td></tr><tr><td rowspan=1 colspan=4>Start Processing</td></tr><tr><td rowspan=1 colspan=4>Stop Processing</td></tr></table>

## 6.3.3.6 Monitor Menu

<table><tr><td rowspan=1 colspan=1>EXIT</td><td rowspan=1 colspan=1>SETUP</td><td rowspan=1 colspan=1>TEST</td><td rowspan=1 colspan=1>CONTROL</td><td rowspan=1 colspan=1>MONITOR</td><td rowspan=1 colspan=1>FILES</td><td rowspan=1 colspan=1>REPORTS</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=5>TBD</td><td rowspan=1 colspan=1></td></tr></table>

## 6.3.3.7 Files Menu

<table><tr><td rowspan=1 colspan=1>EXIT</td><td rowspan=1 colspan=2>SETUP</td><td rowspan=1 colspan=1>TEST</td><td rowspan=1 colspan=1>CONTROL</td><td rowspan=1 colspan=1>MONITOR</td><td rowspan=1 colspan=1>FILES</td><td rowspan=1 colspan=1>REPORTS</td></tr><tr><td rowspan=5 colspan=2></td><td rowspan=1 colspan=5>Enable File Transfer</td><td rowspan=5 colspan=1></td></tr><tr><td rowspan=1 colspan=5>Disable File Transfer</td></tr><tr><td rowspan=1 colspan=5>Retain Indefinitely ...</td></tr><tr><td rowspan=1 colspan=5>Delete NOW ...</td></tr><tr><td rowspan=1 colspan=5>Resend DAN ...</td></tr></table>

## 6.3.3.8 Reports Menu

<table><tr><td>EXIT</td><td>SETUP</td><td>TEST</td><td>CONTROL</td><td>MONITOR</td><td>FILES</td><td>REPORTS</td></tr><tr><td rowspan="4"></td><td rowspan="4"></td><td colspan="5">Data Receive Summary </td></tr><tr><td colspan="5">Return Link Q&amp;A ...</td></tr><tr><td colspan="4">Level 0R Q&amp;A ...</td></tr><tr><td colspan="4">File Transfer Summary All Contact Reports ...</td></tr></table>

## 7.0 LPS Operational Scenarios

The LPS operational scenarios represent sequences of activities performed by operations personnel as they relate to the LPS software. The scenarios may be divided into the categories of normal operations, those performed routinely to accomplish Landsat 7 data processing within the LPS, and contingency operations, those performed in response to abnormal conditions. Within each of these categories, the operational scenarios described in this section are as follows.

• Normal Operations

Receive Contact Schedule from the LGS.

Receive Parameters from the IAS.

\- Set Up LPS Strings for Data Capture.

Receive Data from the LGS.

Process Data to Level 0R.

Transfer Data to the LP DAAC.

Reprocess LPS Data.

\- Support Operational Training and Test.

• Contingency Operations

\- Adjust LPS Level 0R Parameters.

Adjust LPS Level 0R Thresholds.

Respond to Failure in LGS-to-LPS or LPS-to-LP DAAC Connection.

\- Respond to Exhaustion of LPS Output Storage Capacity.

\- Respond to LPS String Failure

These categories represent the majority of the activities performed by LPS operations personnel.

The operational scenarios are strongly affected by the LPS architecture presented in figure 7-1. The LPS architecture includes 5 logically independent processing strings. LPS operations use 4 processing strings at all times to support normal operations. The fifth string is available for LPS test and maintenance support, as required, as a back-up string for the 4 operational strings, and as a site for operations training and testing. The architecture also includes two workstations. One serves as the console for interface to the 4 operational strings. The second is available as an interface to the back-up string, for LPS maintenance support, as required, and as a back-up to the operational interface workstation.

Figure 7-1 LPS Interconnect Architecture  
![](images/bbbd043aadf2bc0ab44d60185587fef80a736a2e28873ab889987ae0f98b9a0d.jpg)

Because of the independence between LPS strings, operations involving the 4 operational strings require that the same procedure be repeated separately on each string. However, these operations may be performed from the single interface workstation via remote login windows to each operational string.

## 7.1 Normal Operations

Normal LPS operations scenarios describe the sequences of operator activities performed routinely to accomplish Landsat 7 data processing within the LPS.

## 7.1.1 Receive Contact Schedule from the LGS

The LPS operator receives a hard-copy contact schedule from the LGS operator. The LPS operator inputs the schedule to the LPS software on each LPS string. The steps performed by the operator when a contact schedule is received are as follows.

1. Insert the new contact schedule into each LPS string database by selecting the LPS software menu option to modify contact schedules.

## 7.1.2 Receive Parameters from the IAS

The LPS operator receives a hard-copy list of IAS parameters from the IAS. The LPS operator inputs the parameters to the LPS software on each LPS string. The steps performed by the operator when a list of IAS parameters is received are as follows.

1. Insert the new IAS parameters into the LPS back-up string database by selecting the LPS software menu option to modify IAS parameters.

2. Execute LPS functions test for LPS functions and product verification on the back-up string.

3. Verify that outputs are correct.

4. Insert the new IAS parameters into each active string.

## 7.1.3 Set Up LPS Strings for Data Capture

The LPS operator verifies that the LPS configuration is correct and functional prior to each contact period. The steps in the scenario are carried out for each of the four active LPS strings but are controlled from a single workstation acting as a terminal for each string. The steps performed by the operator for LPS set up are as follows.

1. Coordinate the LGS output channel to LPS string configuration for the contact period. The LPS operator informs the LGS operator of LPS string failures so that a functioning configuration can be defined. The LGS operator implements the necessary switching to establish the agreed upon configuration.

2. Configure LPS strings to LP DAAC communication interfaces.

3. If required, start LPS user interface for each string by bringing up a window for each string and issuing a command in each to start up the LPS user interface.

4. Update the LGS output channel and LP DAAC connection information on each LPS string as required to reflect the new configuration by selecting the LPS software menu option to update LPS string configuration.

6. If required, enter/update LPS parameters for each string as described in section 7.2.1.

7. If required set LPS thresholds for each string as described in section 7.2.2.

8. Set up system monitoring on each string by selecting the LPS software menu option to set up LPS monitoring.

9. Check available disk space for minor data stores (trouble files and the LPS journal) using IRIX system commands; delete, truncate, or roll files off to tape as appropriate until sufficient disk space is available.

10. Check available disk space for raw wideband data store on each string using IRIX system commands. It is an operational decision whether existing files will be deleted or data will not be capture when insufficient disk space is available.

11. Execute LPS functions test for LPS functions and product verification on each LPS string.

## 7.1.4 Receive Data from the LGS

The LPS operator initiates the capture of raw wideband data by an LPS string configured to each LGS output channel which will be active during the contact period. This scenario presupposes the successful execution of the LPS string setup scenario described in section 7.1.3. The steps performed by the operator to receive data from the LGS are as follows.

1. Review contact schedule for data capture times.

2. Start data capture to disk approximately 15 seconds before scheduled acquisition of signal by selecting the LPS software menu option to start data capture for each string.

3. Verify acquisition of signal with LGS operator.

4. Monitor data receipt processes through LPS software status displays.

5. Verify loss of signal with LGS operator.

6. Stop data capture by selecting the LPS software menu option to stop data capture on each string.

7. Print and review a data receive summary report (figure 7- 2) by selecting the LPS software menu option to generate the report for the contact period just captured.

8. Provide MOC with data receive summary via voice link or FAX.

9. Mount tape on drive.

10. Start copy to tape by selecting the LPS software menu option to copy to tape.

11. Label and move tape to 60-day storage.

<table><tr><td>CONTACT PERIODDATA VOLUME RECEIVED</td></tr><tr><td>DATE REC&#x27;DSTART STOPGBYTES APPROX SCENES</td></tr><tr><td>1998 123 09:15:00 09:29:03 7.8833</td></tr></table>

## 7.1.5 Process Data to Level 0R

The LPS operator initiates the processing to level 0R of raw wideband data on each LPS string that stores data for the contact period. The steps performed by the operator to process data to level 0R are as follows.

1. Verify that sufficient space is available in the data transfer store for output products using IRIX system commands. If retained files have been transferred to the LP-DAAC, it is an operational decision whether those files will be deleted or data processing will be delayed.

2. Start processing for selected contact by selecting the LPS software menu option to start level 0R processing.

3. Monitor the data processing function using LPS software status displays.

4. Print and review the return link quality and accounting report (figure 7-3) by selecting the LPS software option to generate this report.

5. Print and review level 0R quality and accounting report (figure 7-4) by selecting the LPS software option to generate this report.

6. Verify data are stored for LP DAAC retrieval using IRIX system commands.

<table><tr><td>LPS RETURN LINK QUALITY AND ACCOUNTING REPORT</td></tr><tr><td>CONTACT PERIOD Date 1998 123 LPS String ID LPS 1 Start 09:15:00 Data Channel 4</td></tr><tr><td>Stop 09:29:03</td></tr><tr><td>Data Received in MBytes 788.01</td></tr><tr><td># Major Frames Received 11870 Approx #WRS Scenes Received 33</td></tr><tr><td>Approx Bit Error Rate 0.000001</td></tr><tr><td></td></tr><tr><td>CADU Sync Information Search: 1</td></tr><tr><td>Lock: 2</td></tr><tr><td>0</td></tr><tr><td>Flywheel: CADU Sync Marker Check: 0</td></tr><tr><td>CADU Sync Lock Error : 0</td></tr><tr><td>#CADUs received: 7572112 #CADUs w/sync errors:</td></tr><tr><td>25 #CADUs missing 10 #CADUs w/CRC errors: 3</td></tr><tr><td>#Flywheel CADUs 5 BCH on mission data zone</td></tr><tr><td></td></tr><tr><td>#CADUs corrected: 10 #CADUs uncorrected: 0 VCDU Headers: BCH on data pointer zone</td></tr><tr><td>#R-S correctable: 2 #CADUs corrected:</td></tr><tr><td>1 #R-S uncorrectable:1 #CADUs uncorrected 0</td></tr></table>

Figure 7-3

Draft Return Link Quality and Accounting Report Format

<table><tr><td>LPS LEVEL OR QUALITY AND ACCOUNTING REPORT</td></tr><tr><td>SUBINTERVAL</td></tr><tr><td>Date 1998 123 LPS String ID LPS 1 Start 09:15:00 Data Channel 4</td></tr><tr><td>Stop 09:29:03</td></tr><tr><td>#Major Frames in SubInterval 11870</td></tr><tr><td>#Major Frame ENTIRELY Filled 24</td></tr><tr><td>#Major Frames PARTIALLY Filled 123</td></tr><tr><td>Approx Bit Error Rate 0.000001</td></tr><tr><td>CADU Sync Information</td></tr><tr><td>Search: 1</td></tr><tr><td>Lock: 2</td></tr><tr><td>Flywheel: 0</td></tr><tr><td>CADU Sync Marker Check: 0</td></tr><tr><td>CADU Sync Lock Error : 0</td></tr><tr><td>#CADUs received: 7572112 #CADUs w/sync errors:</td></tr><tr><td>25 #CADUs missing 10 #CADUs w/CRC errors: 3</td></tr><tr><td>#Flywheel CADUs 5 BCH on mission data zone</td></tr><tr><td>#CADUs corrected: 10</td></tr><tr><td>#CADUs uncorrected: 0 VCDU Headers:</td></tr><tr><td>BCH on data pointer zone #R-S correctable: 2 #CADUs corrected</td></tr><tr><td></td></tr><tr><td>1 #R-S uncorrectable: 1 #CADUs uncorrected 0</td></tr></table>

## Figure 7-4

Draft Level 0R Link Quality and Accounting Report Format

## 7.1.6 Transfer Files to the LP DAAC

Transfer of output files to the LP DAAC occurs automatically unless the override option has been set. This section describes the automatic transfer scenario. The LPS operator monitors the LPS/LP DAAC interface. The steps performed by the operator to monitor the interface are as follows.

1. Monitor interface with LP DAAC via IRIX system utilities.

2. Verify DAN sent to LP DAAC via LPS software status and journal messages.

3. Verify successful transfer of files via LPS software status and journal messages and/or transfer status of files in LPS database.

4. Print and review data transfer summary report (figure 7-5).

5. Monitor deletion of successfully transferred files via LPS software status messages and IRIX system utilities.

<table><tr><td colspan="3">LPS DAILY TRANSFER SUMMARY</td></tr><tr><td>Date: 1998 123</td><td>Available</td><td>Transmitted</td></tr><tr><td>Level OR</td><td>6</td><td>24</td></tr><tr><td>Browse</td><td>2</td><td>4</td></tr><tr><td>Metadata</td><td>2</td><td>4</td></tr><tr><td>Calibration</td><td>2</td><td>4</td></tr><tr><td>Total (octets)</td><td>10927</td><td>21230</td></tr><tr><td>Available Files</td><td colspan="2">Transmitted Files</td></tr><tr><td>xxxxxxxxxxxxxxxxxxxx</td><td colspan="2">XXXXXXXXXXXXXXXXXXXX</td></tr><tr><td>xxxxxxxxxxxxxxxxxxxx</td><td colspan="2">XXXXXXXXXXXXXXXXXXXX</td></tr><tr><td>xxxxxxxxxxxxxxxxxxxx</td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td>xxxxxxxxxxxxxxxxxxxx</td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td>xxxxxxxxxxxxxxxxxxxx</td><td colspan="2">xXxxxxxxxxxxxxxxxxXx</td></tr><tr><td>xxxxxxxxxxxxxxxxxxxx</td><td colspan="2">xxxxxxxxxxxxxxxxxxxx XXXXXXXXXXXXXXXXXXXX</td></tr><tr><td>xxxxxxxxxxxxxxxxxxxx xxxxxxxxxxxxxxxxxxxx</td><td colspan="2">xXxxxxxxxxxxxxxxxxXx</td></tr><tr><td>XXXXXXXXXXXXXXXXXXXX</td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td>xxxxxxxxxxxxxxxxxxxx</td><td colspan="2">XXXXXXXXXXXXXXXXXXXx XXXXXXXXXXXXXXXXXXXX</td></tr><tr><td>xxxxxxxxxxxxxxxxxxxx</td><td colspan="2"></td></tr><tr><td>XXXXXXXXXXXXXXXXXXXX</td><td colspan="2">xxxxxxxxxxxxxxxxxxxx xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2"></td></tr><tr><td></td><td colspan="2"></td></tr><tr><td></td><td colspan="2">xxxxxxxxxxxxxxxxxxxx xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2">xXxxxxxxxxxxxxxxxxXx</td></tr><tr><td></td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2"></td></tr><tr><td></td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2">XXXXXXXXXXXXXXXXXXXX xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2"></td></tr><tr><td></td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2">xXxxxxxxxxxxxxxxxxXx</td></tr><tr><td></td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2">xXxxxxxxxxxxxxxxxxXx</td></tr><tr><td></td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2">XXXXXXXXXXXXXXXXXXXX</td></tr><tr><td></td><td colspan="2">XXXXXXXXXXXXXXXXXXXX</td></tr><tr><td></td><td colspan="2"></td></tr><tr><td></td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2">XXXXXXXXXXXXXXXXXXXx</td></tr><tr><td></td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2"></td></tr><tr><td></td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2">xxxxxxxxxxxxxxxxxxxx</td></tr><tr><td></td><td colspan="2">XXXXXXXXXXXXXXXXXXXx</td></tr></table>

Figure 7-5  
Draft Data Transfer Summary Report Format

## 7.1.7 Reprocess LPS Data

The LPS operator initiates reprocessing for each contact period for which reprocessing has been requested by the IAS and which is still available in 60-day storage. The steps performed by the operator to reprocess data are as follows.

1. Receive reprocessing request from the IAS.

2. Verify requested data are available in 60-day storage.

3. Schedule data reprocessing time.

4. Locate all tapes for contact period in physical storage.

5. Mount each tape on a drive on a separate string.

6. Restage data to be processed (per string) by selecting LPS software menu option to restage data.

7. Return tapes to physical storage.

8. Initiate level 0R processing as described in section 7.1.5.

The LPS operational timeline, presented in figure 7-6, includes sufficient available time for reprocessing the required 10% of the LPS daily data volume.

LPS Operational Cycle - 24 Hours  
Figure 7-6 LPS Operational Timeline  
![](images/ffb774e493c68667aa143a459f26d1222eaf3e98fce626370964bbfd1011ce62.jpg)

## 7.1.8 Support Operational Training and Test

Operational training and test support is provided by the back-up LPS string and test console with DAN transmission capabilities disabled. Test data output by the LGS may be used to support training in data capture and level 0R processing procedures. Back-up copies of LPS database contents from active strings may be used to populate a training/test database.

## 7.2 Contingency Operations

Contingency operations scenarios describe the sequences of operator activities performed to handle abnormal conditions during Landsat 7 data processing within the LPS. Abnormal conditions include hardware failures and storage capacity shortfalls.

## 7.2.1 Adjust LPS Level 0R Parameters

The LPS operator adjusts LPS Level 0R parameters whenever it is determined that Level 0R output can be increased by adjusting the processing parameters listed in section 6.1.5. The steps performed by the operator to adjust Level 0R parameters are as follows.

1. Determine desired values for parameters.

2. Adjust level 0R parameters on the LPS back-up string by selecting the LPS software menu options that adjust level 0R processing parameters.

3. Execute LPS functions test for LPS functions and product verification on the back-up string.

4. Verify that outputs are correct.

5. Adjust level 0R parameters on each LPS operational string.

## 7.2.2 Adjust LPS Level 0R Thresholds

The LPS operator can adjust LPS Level 0R thresholds described in section 6.1.5 whenever excessive noise in raw wideband data causes a proliferation of alarms and alerts. The steps performed by the operator to adjust level 0R thresholds are as follows.

1. Determine desired values for thresholds for each error type.

2. Adjust level 0R thresholds on each LPS string by selecting the LPS software menu options that adjust level 0R thresholds.

## 7.2.3 Respond to Failure in LGS/LPS Interface

Either the LPS or LGS operator may detect a LGS/LPS interface failure. The steps performed by the LPS operator to respond to a failure in the LGS/LPS interface are as follows.

1. If the LPS operator has detected the failure, then notify the LGS operator.

2. If the failure occurs while data is being captured, notify the MOC and the LP-DAAC of the data loss.

3. Continue level 0R processing on any data captured prior to the failure, including a partial contact period.

4. When the LGS/LPS interface has been restored, coordinate with the LGS operator to test the interface by capturing a test data set sent from the LGS.

5. Verify the successful transmission of the test data set.

## 7.2.4 Respond to Failure in LPS/LP-DAAC Interface

The LPS operator may detect an LPS/LP-DAAC interface failure while monitoring LPS disk space available for transfer storage. The LPS operator may also be notified of the failure by the LP-DAAC operator. The steps performed by the operator to handle this condition are as follows.

1. If the LPS operator has detected the failure, then notify the LP-DAAC operator.

2. Do not perform additional level 0R processing.

3. Continue to capture data and to copy the captured data to the 60-day store; ensure sufficient capture capacity by deleting on-line captured data sets copied to the 60-day store.

4. Resume level 0R processing when the interface is restored.

5. Handle processing for the back-log of data in the 60-day store in the same way as reprocessing as described in section 7.1.7.

The LPS operational timeline, presented in figure 7-6, includes sufficient excess time to support the additional processing load imposed by the suspension of level 0R processing during the interface failure.

## 7.2.5 Respond to Exhaustion of LPS Output Storage Capacity

The LPS operator detects that LPS output storage capacity has been exceeded while monitoring the output storage available on LPS strings. The steps performed by the operator to handle this condition are as follows.

1. Continue receiving data from the LGS as scheduled.

2. Do not initiate level 0R processing on any received data until output storage is available. Coordinate with LP DAAC operator in regard to the LP DAAC schedule for transferring retained files.

## 7.2.6 Respond to LPS String Failure

LPS string failures occur whenever the LPS string Data Process HWCI or any of its peripheral HWCIs fails. The failure of any part of the string is treated identically to a failure of the whole. The steps performed by the operator to handle LPS string failures are as follows.

1. Coordinate with the LGS operator to switch the LGS output channel received by the failed string to the back-up string.

2. Coordinate with LP DAAC operator to determine new LP DAAC connection.

3. Set up the back-up LPS string to replace the failed operational string, following the scenario described in section 7.1.3.

4. Initiate data capture and level 0R processing of captured data on the back-up string.

4. Notify LPS maintenance personnel of the failure.

4. Notify the LP DAAC operator of the failure and cancel any DANs outstanding from the failed string.

5. Reprocess data that was processed by the failed string but not yet transferred to the LP DAAC from the 60-day store to any string with excess processing capacity following the scenario described in section 7.1.7.

6. Stage data captured by the failed string and copied to the 60 day store but not yet processed, then stage the data to any string with excess processing capacity following the scenario for reprocessing described in section 7.1.7.

7. When the failed LPS string has been restored, notify the LP DAAC operator that the restored string will be made operational.

8. Verify that all data available has been transferred to the LP DAAC from the back-up string.

9. Coordinate with the LGS operator to switch the LGS output channel routed to the back-up string to the restored operational string.

10. Set up the restored string to replace the back-up string, following the scenario described in section 7.1.3.

11. Initiate data capture and level 0R processing of captured data on the restored string.

12. Initiate level 0R processing for any captured data on the restored string's disks that have not yet been processed by another string.

The LPS operational timeline, presented in figure 7-6, includes sufficient excess time to support the additional processing load imposed on the remaining operational strings by the need to process data from the failed string.

## Appendix A - Requirements Traceability

This appendix presents the LPS requirements traceability. The first table shows the mapping between F&PS requirements and the lowest level processes in the data flow diagrams. The second table shows the mapping between the lowest level processes in the data flow diagrams and the F&PS requirements. Note that some system and performance requirements which apply to every processes are not shown in the tables.

## A.1 System to Software Requirements Traceability

Requirement Process Process   
Number Number Name   
3.1. 4 2 Synchronize CCSDS Frame 2 Process CCSDS Grade 3 2 Decode BCH 2 Generate Return Link QA Report 2 Validate RDP Parameters 2 Compute BER 2.2 Perform SCLF Sync 2.2 Align Bytes 2.2 Deinvert Data 2.2 Perform PN Decode 2.3 Perform CRC Check 2.3 Perform RS\_EDAC Check 2.3 Discard Fill CADUs 2 Annotate VCID Change   
3.1. 5 3.5 Align Bands 5 Generate Band File 5.2 Reduce Image by Wavelets 5.2 Reduce Image by Subsamples 6 Generate Metadata   
3.1. 6 2 Decode BCH 2 Generate Return Link QA Report 2 Validate RDP Parameters 2 Compute BER 2.3 Perform CRC Check 2.3 Perform RS\_EDAC Check   
3.1. 7 3 Generate Level 0R QA Report   
3.1. 8 6 Process LPS Directive   
3.1.10 6.1 LPS System Control   
3.1.10.1 6.1 LPS System Control   
3.1.10.3 2 Decode BCH 2 Validate RDP Parameters 2 Compute BER 2.2 Perform SCLF Sync 2.3 Perform CRC Check 2.3 Perform RS\_EDAC Check 6 Report LPS Status   
3.1.10.4 6 Monitor System Faults   
3.1.10.5 6 Monitor System Faults   
3.1.11 2 Synchronize CCSDS Frame 2 Validate RDP Parameters 6 Report LPS Status 6 Process LPS Directive   
3.1.12 2 Decode BCH 2 Validate RDP Parameters 2 Compute BER 2.2 Perform SCLF Sync 2.3 Perform CRC Check 2.3 Perform RS\_EDAC Check 6 Report LPS Status   
3.1.14 6.1 Modify LPS Configuration   
3.1.19 6 Report LPS Status   
3.2.2 7 Send DAN 7 Transfer Files   
3.2.4 6 Process LPS Directive   
3.3.1. 1 1 Receive Raw Wideband Data 1 Delete Raw Wideband Data   
3.3.1. 2 1 Receive Raw Wideband Data 1 Delete Raw Wideband Data   
3.3.1. 3 1 Receive Raw Wideband Data 1 Delete Raw Wideband Data   
3.3.1. 4 1 Receive Raw Wideband Data 1 Delete Raw Wideband Data   
3.3.1. 7 1 Save Raw Wideband Data   
3.3.1. 8 1 Save Raw Wideband Data   
3.3.1. 9 1 Restage Raw Wideband Data   
3.3.1.12 1 Receive Raw Wideband Data   
3.3.2. 1 2.3 Perform CRC Check 2.3 Perform RS\_EDAC Check 2.3 Discard Fill CADUs   
3.3.2. 3 2.2 Perform SCLF Sync 2.2 Align Bytes 2.2 Deinvert Data   
3.3.2. 4 2.2 Perform SCLF Sync   
3.3.2. 5 2.2 Deinvert Data   
3.3.2. 6 2.2 Perform SCLF Sync   
3.3.2. 7 2.2 Perform PN Decode   
3.3.2. 8 2.3 Perform CRC Check 2.3 Perform RS\_EDAC Check   
3.3.2. 9 2 Decode BCH   
3.3.2. 9.1 2 Decode BCH   
3.3.2.10 2 Decode BCH   
3.3.2.11 3.4 Determine Subintervals 2 Annotate VCID Change   
3.3.2.12 2.3 Discard Fill CADUs   
3.3.2.13 2 Decode BCH 2 Compute BER 2.2 Perform SCLF Sync 2.3 Perform CRC Check 2.3 Perform RS\_EDAC Check 3.4 Extract and Collect VCDU Quality and Accounting 3.4 Collect VCDU Quality and Accounting   
3.3.2.14 3.4 Identify Major Frames   
3.3.2.15 3.4 Identify Major Frames   
3.3.2.16 3.5 Deinterleave and Reverse Bands   
3.3.5.5 7 Delete LPS Files   
3.3.5.6 7 Retain LPS Files   
3.3.5.7 7 Generate Transfer Summary Report   
3.3.6.1 2 Validate RDP Parameters 6 Process LPS Directive 6.1 Modify Contact Schedule 3 Validate MFP Parameters 5 Validate IDP Parameters   
3.3.6.2 2 Decode BCH 2 Generate Return Link QA Report 2 Compute BER 2.2 Perform SCLF Sync 2.3 Perform CRC Check 2.3 Perform RS\_EDAC Check   
3.3.6.3 6 Process LPS Directive 3 Generate Level 0R QA Report 6 Display or Print LPS Report   
3.3.6.4 6 Process LPS Directive 6 Display or Print LPS Report   
3.3.6.5 6 Process LPS Directive 6 Display or Print LPS Report   
3.3.6.6 4.3 Assemble Minor Frames 5.4 Generate Cloud Cover Assessment 5.4 Collect Scene Data 6 Report LPS Status 6 Process LPS Directive 5 Validate IDP Parameters   
3.3.6.7 4.3 Assemble Minor Frames 5.4 Generate Cloud Cover Assessment 5.4 Collect Scene Data 6 Report LPS Status 5 Validate IDP Parameters   
3.3.6.8 1 Receive Raw Wideband Data 1 Restage Raw Wideband Data 1 Save Raw Wideband Data 2 Synchronize CCSDS Frame 2 Validate RDP Parameters 6 Process LPS Directive 7 Delete LPS Files 7 Retain LPS Files   
3.3.6.9 1 Receive Raw Wideband Data 2 Synchronize CCSDS Frame 6 Process LPS Directive 6.1 LPS System Control   
4.1.6 2 Synchronize CCSDS Frame 2 Process CCSDS Grade 3 2 Decode BCH 2 Generate Return Link QA Report 2 Validate RDP Parameters 2 Compute BER 2.2 Perform SCLF Sync 2.2 Align Bytes 2.2 Deinvert Data 2.2 Perform PN Decode 2.3 Perform CRC Check 2.3 Perform RS\_EDAC Check 2.3 Discard Fill CADUs 2 Annotate VCID Change

<table><tr><td>3.3.2.17</td><td>3.5</td><td>Deinterleave and Reverse Bands</td><td></td><td></td></tr><tr><td>3.3.2.18</td><td>3.5</td><td>Deinterleave and Reverse Bands</td><td></td><td></td></tr><tr><td>3.3.2.19</td><td>3.5</td><td>Deinterleave and Reverse Bands</td><td></td><td></td></tr><tr><td></td><td>3.5</td><td>Align Bands</td><td></td><td></td></tr><tr><td>3.3.2.20</td><td>3.6</td><td>Extract MSCD Data</td><td></td><td></td></tr><tr><td>3.3.2.21</td><td>3.6</td><td>Extract Calibration Data</td><td></td><td></td></tr><tr><td>3.3.2.22</td><td>3.5</td><td>Align Bands</td><td></td><td></td></tr><tr><td>3.3.2.23</td><td>3.4</td><td>Determine Subintervals</td><td></td><td></td></tr><tr><td>3.3.2.24</td><td>3.5</td><td>Deinterleave and Reverse Bands</td><td></td><td></td></tr><tr><td rowspan="6">3.3.2.25</td><td>3.5</td><td>Align Bands</td><td></td><td></td></tr><tr><td>5 3.6</td><td>Generate Band File</td><td></td><td></td></tr><tr><td></td><td>Create MSCD File</td><td></td><td></td></tr><tr><td>3.6</td><td>Extract MSCD Data</td><td></td><td></td></tr><tr><td>4</td><td>Create PCD File</td><td></td><td></td></tr><tr><td>5.2</td><td>Generate Band File</td><td></td><td></td></tr><tr><td rowspan="11">3.3.2.26</td><td>5</td><td>Reduce Image by Wavelets</td><td></td><td></td></tr><tr><td>5.2</td><td></td><td></td><td></td></tr><tr><td>3</td><td></td><td>Reduce Image by Subsamples</td><td></td></tr><tr><td>3.4</td><td>Identify VCDUs</td><td></td><td></td></tr><tr><td>3.4</td><td>Identify Major Frames</td><td></td><td></td></tr><tr><td>3.4</td><td>Extract and Collect vCDU Quality and</td><td>Determine Subintervals</td><td></td></tr><tr><td rowspan="2"></td><td></td><td>Accounting</td><td></td></tr><tr><td>3.4</td><td>Collect vCDU Quality and Accounting</td><td></td></tr><tr><td>3.3.2.27</td><td>4</td><td>Extract Major Frame Info</td><td></td></tr><tr><td></td><td>5</td><td>Generate Band File</td><td></td></tr><tr><td>3.3.2.28</td><td>3.5</td><td>Align Bands</td><td></td></tr><tr><td rowspan="2">3.3.2.29</td><td>5</td><td>Generate Band File</td><td></td></tr><tr><td>4.4</td><td>Compute Position MJF Time</td><td></td><td></td></tr><tr><td>3.3.3.1</td><td>5.2</td><td>Reduce Image by Wavelets</td><td></td><td></td></tr><tr><td rowspan="2"></td><td>5.2</td><td>Reduce Image by Subsamples</td><td></td><td></td></tr><tr><td>5.2</td><td>Reduce Image by Wavelets</td><td></td><td></td></tr><tr><td rowspan="2">3.3.3.2</td><td>5.2</td><td>Reduce Image by Subsamples</td><td></td><td></td></tr><tr><td>5.2</td><td>Reduce</td><td></td><td></td></tr><tr><td rowspan="2">3.3.3.3</td><td>5.2</td><td>Reduce Image by Subsamples</td><td>Image by Wavelets</td><td></td></tr><tr><td>5.2</td><td></td><td></td><td></td></tr><tr><td>3.3.3.4 3.3.3.5</td><td>5.2</td><td>Reduce Reduce</td><td>Image by Subsamples</td><td></td></tr><tr><td rowspan="2"></td><td>5.2</td><td>Reduce</td><td>Image by Wavelets</td><td></td></tr><tr><td>4.2</td><td></td><td>Image by Subsamples</td><td></td></tr><tr><td>3.3.4. 1</td><td></td><td>Extract Info Word</td><td></td><td></td></tr><tr><td>3.3.4. 2</td><td>3 4.3</td><td>Extract PCD</td><td></td><td></td></tr><tr><td rowspan="2"></td><td>4.3</td><td>Assemble Major Frames</td><td>Assemble Minor Frames</td><td></td></tr><tr><td>4.3</td><td></td><td></td><td></td></tr><tr><td>3.3.4. 3 3.3.4. 4</td><td>4</td><td>Create PCD File</td><td>Assemble Major Frames</td><td></td></tr><tr><td>3.3.4. 5</td><td>4</td><td>Create PCD File</td><td></td><td></td></tr><tr><td></td><td>4.3</td><td>Build PCD Cycles</td><td></td><td></td></tr><tr><td>3.3.4. 6</td><td>4.3</td><td>Build PCD Cycles</td><td></td><td></td></tr><tr><td>3.3.4. 7</td><td>4.4</td><td>Determine WRS Scene Coordinates</td><td></td><td></td></tr><tr><td>3.3.4. 8</td><td>5.4</td><td>Generate Cloud Cover Assessment</td><td></td><td></td></tr><tr><td rowspan="2">3.3.4. 9</td><td>5.4</td><td>Collect Scene Data</td><td></td><td></td></tr><tr><td>5.4</td><td>Generate Cloud Cover Assessment</td><td></td><td></td></tr><tr><td>3.3.4.10</td><td>5.4</td><td>Generate Cloud Cover Assessment</td><td></td><td></td></tr><tr><td>3.3.4.11</td><td>6</td><td>Generate Metadata</td><td></td><td></td></tr><tr><td>3.3.4.12</td><td>6</td><td>Generate Metadata</td><td></td><td></td></tr><tr><td>3.3.5.1</td><td>7</td><td>Send DAN</td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td></tr><tr><td>3.3.5.2</td><td>7</td><td>Transfer Files</td><td></td><td></td></tr><tr><td>3.3.5.3</td><td>7</td><td>Receive DTA</td><td></td><td></td></tr><tr><td rowspan="2">3.3.5.4</td><td>7</td><td>Delete LPS Files</td><td></td><td></td></tr><tr><td>7</td><td>Retain LPS Files</td><td></td><td></td></tr></table>

<table><tr><td>4.3.3</td><td>2</td><td colspan="2">Synchronize CCSDS Frame</td></tr><tr><td>4.3.4</td><td>5.2</td><td>Reduce Image by Wavelets</td><td></td></tr><tr><td rowspan="2">4.3.5</td><td>5.2</td><td>Reduce Image by Subsamples</td><td></td></tr><tr><td>4.4</td><td></td><td>Determine WRS Scene Coordinates</td></tr></table>

## A.2 Software to System Requirements Traceability

Process Process Requirement   
Number Name Number   
1 Receive Raw Wideband Data 3.3.1. 1   
3.3.1. 2   
3.3.1. 4   
3.3.6.8   
3.3.6.9   
3.3.1.12   
3.3.1. 3   
1 Restage Raw Wideband Data 3.3.1. 9   
3.3.6.8   
1 Save Raw Wideband Data 3.3.1. 7   
3.3.1. 8   
3.3.6.8   
1 Delete Raw Wideband Data 3.3.1. 1   
3.3.1. 4   
3.3.1. 2   
3.3.1. 3   
1 Generate Data Receive Summary Report   
2 Generate Return Link QA Report 3.1. 4   
4.1.6   
3.3.6.2   
3.1. 6   
2 Decode BCH 3.1. 4   
3.1. 6   
3.1.12   
3.1.10.3   
3.3.2. 9.1   
3.3.2.13   
4.1.6   
3.3.6.2   
3.3.2.10   
3.3.2. 9   
2 Annotate VCID Change 3.1. 4   
4.1.6   
3.3.2.11   
2 Process CCSDS Grade 3 3.1. 4   
4.1.6   
2 Validate RDP Parameters 3.1. 4   
3.1. 6   
4.1.6   
3.3.6.8   
3.3.6.1   
3.1.12   
3.1.11   
3.1.10.3   
2 Compute BER 3.1. 4   
3.3.6.2   
3.3.2.13   
3.1. 6   
4.1.6   
PS/MO&DSD A - 6 April 28, 1995 April 28, 19   
3.1.12   
3.1.10.3   
2 Synchronize CCSDS Frame 3.1. 4   
4.3.3   
4.1.6   
3.1.11   
3.3.6.9   
3.3.6.8   
2.2 Perform PN Decode 3.1. 4   
3.3.2. 7   
4.1.6   
2.2 Deinvert Data 3.1. 4   
4.1.6   
3.3.2. 5   
3.3.2. 3   
2.2 Align Bytes 3.1. 4   
3.3.2. 3   
4.1.6   
2.2 Perform SCLF Sync 3.1. 4   
4.1.6   
3.3.6.2   
3.3.2.13   
3.1.12   
3.3.2. 3   
3.1.10.3   
3.3.2. 6   
3.3.2. 4   
2.3 Perform CRC Check 3.1. 4   
4.1.6   
3.3.2.13   
3.3.6.2   
3.3.2. 8   
3.1.12   
3.3.2. 1   
3.1.10.3   
3.1. 6   
2.3 Discard Fill CADUs 3.1. 4   
3.3.2. 1   
4.1.6   
3.3.2.12   
2.3 Perform RS\_EDAC Check 3.1. 4   
4.1.6   
3.3.6.2   
3.3.2.13   
3.3.2. 8   
3.1. 6   
3.1.10.3   
3.1.12   
3.3.2. 1   
3 Validate MFP Parameters 3.3.6.1   
3 Generate Level 0R QA Report 3.1. 7   
3.3.6.3   
3 Extract PCD 3.3.4. 2   
3 Identify VCDUs 3.3.2.26   
3 Parse Major Frame   
3 Extract Calibration and MSCD   
3 Collect Quality and Accounting   
3 Generate Band Data   
3.4 Determine Subintervals 3.3.2.11   
3.3.2.23   
3.3.2.26   
3.4 Extract Major Frame Time   
3.4 Collect VCDU Quality and Accounting 3.3.2.13   
3.3.2.26   
3.4 Identify Major Frames 3.3.2.14   
3.3.2.15   
3.3.2.26   
3.5 Deinterleave and Reverse Bands 3.3.2.16   
3.3.2.17   
3.3.2.24   
3.3.2.18   
3.3.2.19   
3.5 Align Bands 3.1. 5   
3.3.2.24   
3.3.2.19   
3.3.2.22   
3.3.2.28   
3.6 Create MSCD File 3.3.2.25   
3.6 Extract Calibration Data 3.3.2.21   
3.6 Extract MSCD Data 3.3.2.20   
3.3.2.25   
3.6 Create Calibration File   
4 Calculate Scene Info   
4 Create PCD File 3.3.2.25   
3.3.4. 4   
3.3.4. 5   
4 Extract Major Frame Info 3.3.2.27   
4 Assemble PCD Cycles   
4 Determine PCD Info Word   
4 Validate PCD Parameters   
4.2 Determine Majority Info Word   
4.2 Extract Info Word 3.3.4. 1   
4.3 Assemble Major Frames 3.3.4. 2   
3.3.4. 3   
4.3 Build PCD Cycles 3.3.4. 5   
3.3.4. 6   
4.3 Assemble Minor Frames 3.3.4. 2   
3.3.6.7   
3.3.6.6   
4.4 Calculate Sun Position   
4.4 Determine WRS Scene Coordinates 3.3.4. 7   
4.3.5   
4.4 Report Scene Info   
4.4 Compute Horizontal Display Shift   
4.4 Compute Position MJF Time 3.3.2.29   
4.4 Compute Latitude And Longitude   
5 Perform ACCA   
5 Validate IDP Parameters 3.3.6.1   
3.3.6.6   
3.3.6.7   
5 Generate Band File 3.1. 5   
3.3.2.28   
3.3.2.27   
3.3.2.25   
3.3.2.24   
5 Generate Browse File   
LPS/MO&DSD A - 8 April 28, 1995   
5.2 Reduce Image by Wavelets 3.1. 5   
4.3.4   
3.3.3.5   
3.3.3.1   
3.3.3.2   
3.3.3.3   
3.3.2.25   
5.2 Reduce Image by Subsamples 3.1. 5   
4.3.4   
3.3.3.5   
3.3.3.4   
3.3.3.3   
3.3.3.2   
3.3.3.1   
3.3.2.25   
5.4 Collect Scene Data 3.3.4. 8   
3.3.6.7   
3.3.6.6   
5.4 Generate Cloud Cover Assessment 3.3.4. 8   
3.3.4.10   
3.3.6.7   
3.3.6.6   
3.3.4. 9   
6 Generate Metadata 3.1. 5   
3.3.4.11   
3.3.4.12   
6 Report LPS Status 3.1.10.3   
3.1.12   
3.1.19   
3.1.11   
3.3.6.7   
3.3.6.6   
6 Process LPS Directive 3.1. 8   
3.1.11   
3.3.6.9   
3.3.6.8   
3.3.6.6   
3.3.6.5   
3.3.6.4   
3.3.6.3   
3.3.6.1   
3.2.4   
6 Display or Print LPS Report 3.3.6.3   
3.3.6.4   
3.3.6.5   
6 Monitor System Faults 3.1.10.4   
3.1.10.5   
6.1 LPS System Control 3.1.10.1   
3.1.10   
3.3.6.9   
6.1 Modify LPS Configuration 3.1.14   
6.1 Modify Contact Schedule 3.3.6.1   
7 Control Send DAN   
7 Generate Transfer Summary Report 3.3.5.7   
7 Retain LPS Files 3.3.5.4   
3.3.5.6   
3.3.6.8   
7 Transfer Files 3.2.2   
3.3.5.2   
7 Delete LPS Files 3.3.5.4   
3.3.5.5   
3.3.6.8   
7 Receive DTA 3.3.5.3   
7 Generate DAN   
7 Send DAN 3.2.2   
3.3.5.1

## Appendix B - Data Dictionary

ACCA

( data

= Scene\_Id + CCA\_Quadrant1\_Score + CCA\_Quadrant2\_Score + CCA\_Quadrant3\_Score + CCA\_Quadrant4\_Score + CCA\_Aggregate\_Score.

Five percentage scores indicating the amount of cloud coverage including one score for each quadrant and one aggregate score for an entire WRS scene. The metadata contains the scene id and sub interval id to uniquely identify the scores. \*

-------- end definition ---

ACCA\_Acct

( data

= Sub\_Intv\_Id + CCA\_Method + ACCA.

File containing the CCA method and the ACCA scores. This information is stored in the datastore IDP\_Acct. \*

-------- end definition --------

Actual\_Center\_Coords

( data

= Sub\_Intv\_Id + Longitude + Latitude + Scene\_Center\_Time. \*

The computed scene center position and corresponding time. There is one set of information for each identified scene. \*

-------- end definition ----

Actual\_Time

( data

)

= Real.\*

The actual major frame time to 1/16th of a millisecond.

-------- end definition ---

Address

( data

= \* Internal location of data. \*. end definition

ADS

( data

= Byte. \* The result of the sample of up to four Attitude Displacement Sensor related temperatures. Each sample is inserted into two consecutive bytes of the PCD minor frame. There will be eight

ADS-related bytes in total. \* ---------- end definition --

Aligned\_Bands

( data

= Sub\_Intv\_Id +   
[ Fmt1\_Align\_Data | Fmt2\_Align\_Data   
]. \*

Band data after all alignments have been performed. This is done according to the Sensor\_Alignment\_Info.

-------- end definition -----

Aln\_CADU

( data

= Contact\_Id + Sync + CADU\_Bytes + Sync\_Annotation \*

A CADU which has been aligned on a byte boundary with the sync quality indicators

NOTE:   
The contact ID is not part of the annotation, but simply shown as information necessary to associate this CADU with a Contact\_Id.   
\*

------- end definition -- = Contact\_Id + Inverted\_Sync + Inverted\_CADU\_Bytes + Sync\_Annotation \*

An inverted CADU which has been aligned on a byte boundary with the sync quality indicators

NOTE:

The contact ID is not part of the annotation, but simply shown as information necessary to associate this CADU with a Contact\_Id.   
\*

-------- end definition -----

Ann\_CADU

( data

= Contact\_Id + Sync + PN\_Decoded\_CADU\_Bytes + Sync\_Annotation

A CADU that includes the sync marker, the bytes that have been PN decoded and the frame sync quality annotations.

NOTE:

The contact ID is not part of the annotation, but simply shown as information necessary to associate this CADU with a Contact\_Id.

-------- end definition ---

Ann\_VCDU ( data )   
= Contact\_Id +   
Sync +   
VCDU\_Hdr\_Bytes +   
[   
VCDU\_Data |   
BCH\_Corrected\_Data   
] +   
VCDU\_Trailer +   
Sync\_Annotation +   
CRC\_Annotation +   
RS\_Annotation +   
BCH\_Annotation +   
VCID\_Change\_Flag.   
\*

A VCDU that has completed all of the error detection and correction processes and has been checked for a change in VCID along with the data quality annotations and a flag to indicate a change in the VCID.

The Contact ID and End\_Of\_Contact\_Flag are not part of the annotation, but simply shown as information necessary to associate this VCDU with a Contact\_Id and the end of contact.

------- end definition ---

Ann\_VCDU\_Collection ( store )   
= Rel\_VCDU\_Cnt +   
0{   
Ann\_VCDU +   
Num\_Missing\_VCDUs   
}Rel\_VCDU\_Cnt +   
Exp\_VCDU\_Ctr +   
Exp\_Mnf\_Ctr +   
Mjf\_CADU\_Seq\_Err\_Cnt +   
Mjf\_CADU\_Fly\_Cnt +   
Mnf\_Ctr\_Err   
\*   
The storage for annotated VCDUs during major frame creation.   
\*   
- end definition

App\_Data\_Band1 ( data )   
= {   
Byte   
} +   
Status\_Info +   
Drift\_Time.   
\*   
Format 1 Scene Data for band 1 appended with the   
Status\_Info and Drift\_Time.   
\*   
- end definition

App\_Data\_Band2 ( data )   
= {   
Byte   
} +   
Status\_Info +   
Drift\_Time.   
\*   
Format 1 Scene Data for band 2 appended with the

```prolog
App_Data_Band6 ( data )
= {
Byte
} +
Status_Info +
Drift_Time.
```

Status\_Info and Drift\_Time. \* ---------- end definition ---------

App\_Data\_Band3 ( data )   
= {   
Byte   
} +   
Status\_Info +   
Drift\_Time.   
\*   
Format 1 Scene Data for band 3 appended with the   
Status\_Info and Drift\_Time.   
\*   
- end definition

App\_Data\_Band4 ( data )   
= {   
Byte   
} +   
Status\_Info +   
Drift\_Time.   
\*   
Format 1 Scene Data for band 4 appended with the   
Status\_Info and Drift\_Time.   
\*   
- end definition

App\_Data\_Band5 ( data ) = { Byte } + Status\_Info + Drift\_Time. \* Format 1 Scene Data for band 5 appended with the Status\_Info and Drift\_Time. \* end definition

Format 1 or 2 Scene Data for band 6 appended with the

Status\_Info and Drift\_Time. \* ---------- end definition ----------

App\_Data\_Band7 ( data )   
= {   
Byte   
} +   
Status\_Info +   
Drift\_Time.   
\*   
Format 2 Scene Data for band 7 appended with the   
Status\_Info and Drift\_Time.   
\*   
- end definition

App\_Data\_Pan ( data )   
= {   
Byte   
} +   
Status\_Info +   
Drift\_Time.   
\*   
Format 2 Pan Data appended with the Status\_Info and   
Drift\_Time.   
\*   
- end definition

App\_Format\_1\_Bands ( data ) = App\_Data\_Band1 + App\_Data\_Band2 + App\_Data\_Band3 + App\_Data\_Band4 + App\_Data\_Band5 + App\_Data\_Band6. \*

Data for bands 1 through 6 appended with the drift time.   
\* ----- end definition -------

App\_Format\_2\_Bands ( data ) = App\_Data\_Band6 + App\_Data\_Band7 +

App\_Data\_Pan.   
\*   
Data for bands 6, 7 and Pan appended with the drift time.   
\* ----- end definition ----

Approx\_Data\_Received ( data )

= Natural. \* The approximate amount of wideband data received in megabytes. \* -- end definition ---

Approx\_ETM\_Count ( data )

= Natural. \* The approximate number of ETM+ scenes. \* - end definition -

Approx\_Major\_Frame\_Count ( data )

= Natural. \* The approximate number of major frames. \* --- end definition -----

Att\_Lower\_Bounds ( data )

= Real. \* The lowest valid value of any attitude component. (TBD) \* -- end definition --

Att\_Upper\_Bounds ( data )

= Real. \* The highest valid value of any attitude component. (TBD) \* - end definition --

Attitude ( data ) = EPA1 + EPA2 + EPA3 + EPA4. \* The components of the quaternion which describes the position of the spacecraft are located in each PCD Major Frame.PCD Minor Frame 0-15.Word 72. \* - end definition -

Available\_Browse\_File\_Count ( data )

= Natural \* Count of available Browse files. \* - end definition -

Available\_L0R\_File\_Count ( data )

= Natural \* Count of available L0R files.

\* end definition -

Available\_LPS\_File\_Names ( data ) = { Contact\_File\_Names }. \* The names of LPS output files which are available for transfer to the LP DAAC but for which a DAN has not yet been sent. \* - end definition --

Available\_Metadata\_Count ( data ) = Natural \* Count of available Metadata files. \* - end definition -

Available\_Retention\_Space ( data )

= Natural. \* This object represents the number of units of volume of disk space which are currently available to be used for on-line retention of LPS output files. \* -- end definition --

Band1\_File\_Type ( data , discrete )

= "Band1". \* A string identifying the Band 1 file. \* - end definition --

Band2\_File\_Type ( data , discrete ) = "Band2". \* A string identifying the Band 2 file. \* - end definition --

Band3\_File\_Type ( data , discrete ) = "Band3". \* A string identifying the Band 3 file. \* - end definition -

Band4\_File\_Type ( data , discrete )

A string identifying the Band 4 file. \* - end definition ---

Band5\_File\_Type ( data , discrete ) = "Band5". \* A string identifying the Band 5 file. \* - end definition -

Band6\_Det\_Data ( data ) = 6313{Byte}6313. \* Aligned detector data for band 6. \* -- end definition -

Band6\_File\_Type

= "Band6". \* A string identifying the Band 6 file. \* - end definition -----

Band7\_File\_Type ( data , discrete ) = "Band7". \* A string identifying the Band 7 file. \* - end definition -

Band\_Acct

= Sub\_Intv\_Id + Bands\_Present + Band\_File\_Names + Band\_Gains + Gain\_Change\_Flag

A datastore containing the sub-interval identifier, the band numbers for which band files were created and the band file names.   
\*

------- end definition --

Band\_Det\_Data

( data )

= 6313{Byte}6313.

The aligned band data array for bands 1 through 5 and 7. Data for each detector consists of 6313 bytes. \*

-------- end definition --

Band\_File

= [ App\_Format\_1\_Bands | App\_Format\_2\_Bands ]. \* A set of files of deinterleaved data with one file per band. Each file has been appended with the Status\_Info and Drift\_Time. Format 1 bands are 1-6; format 2 bands are 6, 7 and Pan. \*

-------- end definition ---

Band\_File\_Name ( data ) = File\_Location + "L7\_" + MF\_Start\_Time + 11 + Band\_File\_Type + + File\_Version\_Number. \* The band file name. \* end definition

Band\_File\_Names ( data ) = [ Band\_File\_Names\_Fmt1 | Band\_File\_Names\_Fmt2 ]. \* There are six band file names for format 1. There are three band file names for format 2. \* -- end definition -

Band\_File\_Names\_Fmt1 ( data ) = 6{ Band\_File\_Name }6. \* The band file names for format 1 data \* - end definition -

Band\_File\_Names\_Fmt2 ( data ) = 3{ Band\_File\_Name }3. \* The band file names for format 2 data \* - end definition -

= [Band1\_File\_Type | Band2\_File\_Type | Band3\_File\_Type | Band4\_File\_Type | Band5\_File\_Type | Band6\_File\_Type | Band7\_File\_Type | Band\_Pan\_File\_Type]

The type of band file generated. \* -- end definition --

Band\_Gain ( data ) = Bit. \* 1 bit of word 8 of the PCD/Status field of the VCDU. This applies to bands 1 through 5 and band 7. Low gain = "0". High gain = "1". \* -- end definition --

Band\_Gain6

( data

Band\_Gain\_Pan

( data

Band gain PAN bit. Word 7 bit 8 of PCD/Status Data.   
Low gain = "0". High gain = "1".   
\* ------ end definition ---

Band\_Gains

( data

\+ Band\_Gain\_Pan

Description:

Band gains for LPS bands (1 to 8).

-------- end definition --

Band\_Num

( data )

The band number of the Aligned\_Bands.Band\_Det\_Data.

Band\_Pan\_File\_Type

( data , discrete )

= "Band\_Pan". \* A string identifying the Pan Band file. \* - end definition --

Band\_Store

( store )

= {Aligned\_Bands}.

A datastore that accumulates the Aligned\_Bands data for Band Processing until the sub-interval changes.

-------- end definition ---

Bands\_Present

( data

, discrete )

= ("1") + ("2") + ("3") + ("4") + ("5") + ("6") + ("7") + ("Pan"). \*

The bands present for the sub-interval.

-------- end definition ---

## BCH\_Acct

( data )

= Contact\_Id + BCH\_Data\_Corrected\_Error\_Count + BCH\_Pointer\_Corrected\_Error\_Count + BCH\_Data\_Uncorrected\_Error\_Count + BCH\_Pointer\_Uncorrected\_Error\_Count.

Aggregate information on the number of Mission Data and Data Pointer Field BCH errors encountered in a data set, including counts of CADUs with BCH corrected errors and of CADUs with BCH uncorrected errors.   
\*

--------- end definition -----

## BCH\_Annotation

( data

= Data\_Field\_Qual\_Indicator + BCH\_Bits\_Corrected. \* The BCH annotations for a CADU. \* --- end definition -------

BCH\_Bits\_Corrected

( data )

= Natural.\*

The total number of bits that were BCH corrected fort the mission data zone in the associated CADU. \*

-------- end definition --

BCH\_Chkd\_VCDU

= Contact\_Id + Sync + VCDU\_Hdr\_Bytes +   
[ VCDU\_Data | BCH\_Corrected\_Data

( data )

] + VCDU\_Trailer + Sync\_Annotation + CRC\_Annotation + RS\_Annotation + BCH\_Annotation.

A VCDU that has completed the BCH Decode EDAC process which could have up to 3 bits corrected in the mission data field, along with the data quality indicators from frame sync, CRC, Reed\_Solomon and BCH Decode process.   
\*

-------- end definition --

BCH\_Corrected\_Data ( data )

= VCDU\_Corrected\_Mission\_Data + 272{Bit}272. \* A VCDU with the mission data zone and/or pointer BCH corrected. \* - end definition --

BCH\_Data\_Corrected\_Error\_Count ( data ) = Natural. \* Number of correctable BCH data field errors which occurred while CCSDS processing a raw wideband data set. \* ----- end definition --

BCH\_Data\_Uncorrected\_Error\_Count ( data )

= Natural. \* Number of uncorrectable BCH data field errors which occurred while CCSDS processing a raw wideband data set. \* --- end definition --

BCH\_Failed\_VCDU ( data )

= Grade\_3\_Chkd\_VCDU.

This is a VCDU which has failed the BCH decode algorithm.

-------- end definition --

BCH\_Pointer\_Corrected\_Error\_Count ( data )

= Natural.

Number of correctable BCH pointer field errors encountered while CCSDS processing a raw wideband data set. \*

------- end definition --

BCH\_Pointer\_Uncorrected\_Error\_Count ( data )

= Natural.

Number of uncorrectable BCH pointer field errors encountered while CCSDS processing a raw wideband data set.

-------- end definition ---

BCH\_Thres

( data )

= Natural

The maximum number of BCH errors allowed before notifying operator. \*

BER

( data )

= Real.\*

The approximate bit error rate computed from a channel's contact period data (0.0...1.0) with TBD precision. \*

-------- end definition ---

BER\_Acct

( data )

= Contact\_Id + BER. \*

The bit error rate accounting information.

-------- end definition -----

BER\_Thres = Real.

( data )

The maximum bit error rate allowed before notifying   
operator.   
\* ---------- end definition --------

Bit ( data , primitive ) = [ "0" | "1" ]. \* A binary digit. \* - end definition

Boolean ( data , primitive ) = [ "TRUE" | "FALSE" ]. \* A flag containing the value of true or false. \* - end definition -

Browse\_Acct ( data ) = Sub\_Intv\_Id + Browse\_File\_Names. \* Contains the names of all browse files associated with the subinterval. \* - end definition -

= ([ (Overlay\_Wave + Mono\_Band\_Wave ) | (Overlay\_Wave + Multi\_Band\_Wave ) | (Overlay\_Wave + Mono\_Band\_Wave + Multi\_Band\_Wave) ]). \*

A datastore containing one or two reduced data-volume image files of the band files of a sub-interval. If format 2, no browse file will exist.

\* end definition ---

= ([ (Mono\_Browse\_File\_Name) | (Multi\_Browse\_File\_Name) | (Mono\_Browse\_File\_Name + Multi\_Browse\_File\_Name) ]). \*

The browse file name. Browse only exists if format 1 data. \*

-------- end definition ---

Browse\_Store

( store )

= {Aligned\_Bands}.

A datastore that accumulates the Aligned\_Bands data for Browse Processing until the sub-interval changes. \*

-------- end definition ---

Byte ( data ) = 8{Bit}8 \* 8 bits \*. end definition

CADU\_Bit\_Slip

( data )

= \* Indicates the bit slip total for the associated CADU. ### TBR ### \* end definition -

CADU\_Bit\_Slip\_Correction\_Extent ( data )= Natural.\*The range of 0-3 bits.\*--- end definition --

CADU\_Bytes ( data ) = 1036{Byte}1036. \* A normal CADU extracted from the raw wideband data. \* - end definition -

CADU\_Check\_Tolerance ( data )

= Natural. \* The range of CADUs from 0-3. \* - end definition -

CADU\_CRC\_Error\_Count ( data )

= Natural. \* Number of CRC errors encountered while CCSDS processing a Raw\_WB\_Data data set. \* end definition --

CADU\_Flywheel\_Count

( data )

= Natural. \* Number of CADUs with flywheel errors encountered while CCSDS processing a raw wideband data set. \* -- end definition -

CADU\_Flywheel\_Flag

( data )

= Boolean. \* A flag indicating that the associated CADU had flywheel errors. \* ---- end definition --

CADU\_Flywheel\_Tolerance

( data )

The range of CADUs from 0-3. \* ---------- end definition -----

CADU\_Missing\_Count ( data )

= Natural. \* Number of missing CADUs noted during CCSDS processing of a raw wideband data set. \* - end definition -

CADU\_Polarity ( data )

= \* The polarity for a particular CADU. ### TBR ### \* --- end definition ---

CADU\_Polarity\_Flag ( data ) = Boolean. \* A flag indicating the polarity of the associated CADU. \* -- end definition -

CADU\_Rcv\_Count

( data )

= Natural. \* Number of CADUs received in a raw wideband data set (Raw\_WB\_Data). \* - end definition -

CADU\_Search\_Tolerance

( data )

= Natural. \* The range of CADUs from 1-3. \* - end definition -

CADU\_Sync\_Error\_Count ( data )

= Natural. \* Number of CADU sync errors encountered while CCSDS processing a raw wideband data set (Raw\_WB\_Data). \* -- end definition --

CADU\_Sync\_Error\_Flag ( data ) = Boolean. \* An indication of bit flips determined by the frame sync process for the associated CADU \* --- end definition -

CADU\_Sync\_Lock\_Error\_Tolerance ( data )= Natural.\*The range of 0-3 bits.\*-- end definition --

CADU\_Sync\_Marker\_Check\_Error\_Tolerance ( data ) = Natural. \* The range of 0-3 bits. \* -- end definition -

Cal\_Data ( store ) = {Byte}. \* The deinterleaved calibration data collected on a minor frame basis for a given subinterval and is stored in the Cal\_File. \* - end definition ---

Cal\_Door\_Activity\_Status ( data )

= Bit. \* The status of the calibration door activity for a given period of time. The Cal\_Door\_Activity\_Status is located in "serial word P" of the third PCD Major Frame.Minor Frame 83.Word 72. bits 2-3 of each

PCD Cycle.   
\* -- end definition ---

Cal\_File = {Byte}. \*

A file containing all of the calibration data received on a   
major frame basis for a given subinterval.   
\* -------- end definition --------

Cal\_File\_Name ( data ) = File\_Location + "L7\_" + MF\_Start\_Time + \_" + Cal\_File\_Type + " + File\_Version\_Number. \* The calibration file name. \* - end definition

Cal\_File\_Type ( data = "Cal". \* A string identifying the Cal file. \* - end definition --

Cal\_Info ( store )

= Cal\_Door\_Activity\_Status. \* Contains information relating the position of the calibration door for a given period of time. The Cal\_Info is generated on a subinterval basis. \* - end definition --

Cardinal ( data , primitive )

Any natural number excluding 0. \*. -- end definition -------

CCA\_Aggregate\_Score ( data )

= Real \* Percentage of scene that is cloud covered \*. end definition -

CCA\_Method ( data ) = String. \* An Operator defined indicator of the CCA method used: Auto method 1 or Auto method 2. \* - end definition -

CCA\_Quadrant1\_Score ( data )

= Real \* Percentage of first quadrant of a scene that is covered with clouds. \* --- end definition --

CCA\_Quadrant2\_Score ( data )

= Real \* Percentage of second quadrant of a scene that is covered with clouds. \* -- end definition --

CCA\_Quadrant3\_Score ( data )

= Real \* Percentage of third quadrant of a scene that is covered with clouds. \*

----- end definition --

CCA\_Quadrant4\_Score

( data )

= Real \* Percentage of fourth quadrant of a scene that is covered with clouds. \* - end definition -

CCA\_Ratio

( data )

= Cardinal \* Defines the reduction ratio to be used in the ACCA algorithm. Valid values are: 4,8,16,32,48. \* - end definition --

Center\_Latitude

( data )

= Real

WRS scene center latitude. The angular distance, measured in degrees, north or south from the equator.   
\*

-------- end definition -----

Center\_Longitude

( data )

= Real.

WRS scene center longitude. Distance east or west on the earth's surface, measured as an arc of the equator between the meridian passing through a particular place and standard meridian.

------- end definition ---

Chan\_Acss\_Acct

( data

)

= Contact\_Id + Valid\_CCSDS\_Parms + CADU\_Polarity + CADU\_Bit\_Slip + CADU\_Sync\_Error\_Count + CADU\_Rcv\_Count + CADU\_Flywheel\_Count +

CADU\_Missing\_Count.

Quality and accounting information derived from CCSDS processing on the channel access layer. \*

------- end definition --

Char ( data , primitive )

= \* 1 byte character. \* end definition

Configuration\_Items ( data )

= LGS\_Channel\_Id + LPS\_Hardware\_String\_Id. \* LPS configuration items. \*

----- end definition --

Contact\_Ended ( data )

= Bit. \* A flag used to indicate the end of a contact period. \* end definition -

Contact\_File\_Names = { Sub\_Intv\_Id + Sub\_Intv\_File\_Names }. \*

( data )

Contains all files associated with each subinterval of the contact.

------- end definition --

Contact\_Id ( data )

= LPS\_Hardware\_String\_Id + LGS\_Channel\_Id + Contact\_Start\_Time +

Contact\_Stop\_Time.   
\*   
Identifies the data set for a contact period.   
\* - end definition ----

Contact\_Schedule\_Id ( data )

= Natural. \* A unique number assigned to a scheduled contact period or acquisition entry in Contact\_Schedules store. \* - end definition -

Contact\_Schedule\_Start\_Time ( data )

= Time. \* Description: The scheduled contact start time. A time format either supported by local clock time or GMT time. \* - end definition --

Contact\_Schedule\_Stop\_Time ( data )

= Time. \* Description: The scheduled contact period stop time. A time format either local time or GMT time \* - end definition --

Contact\_Schedules ( store ) = { @Contact\_Schedule\_Id + Contact\_Schedule\_Start\_Time + Contact\_Schedule\_Stop\_Time }. \* A schedule containing multiple start/stop times that Landsat 7 spacecraft downlinks the wideband data to LGS. The schedule is coming from LGS in a hardcopy form. \* --- end definition --

Contact\_Start\_Time ( store ) = Current\_Time. \* The contact period start time. \* -- end definition -

Contact\_Stop\_Time

( data )

= Current\_Time. \* The contact period stop time. \* --- end definition ---

CRC\_Acct

( data )

= Contact\_Id + CADU\_CRC\_Error\_Count. \*

The cumulative sum generated in performing the CRC check. \*

-------- end definition --

CRC\_Annotation

( data )

An indication as to whether the associated VCDU passed the CRC check.   
\*

end definition --------

CRC\_Chkd\_CADU

( data

= Contact\_Id + Sync + VCDU\_Bytes + VCDU\_Trailer + Sync\_Annotation + CRC\_Annotation.

A CADU that has completed the CRC checks.

NOTE:   
The contact ID is not part of the annotation, but simply shown as information necessary to associate this CADU with a Contact\_Id.

\* end definition -

CRC\_Failed\_CADU

( data )

= Ann\_CADU.

------- end definition --

CRC\_Thres ( data )

= Natural. \* The maximum number of CRC errors allowed before notifying operator \*

------- end definition --

Curr\_VCID ( data )

= VCID \* The VCID of the current VCDU \* end definition

Current\_Orbit

( store )

= Orbit\_Time + Orbit\_Num. \*

The current orbit number and upper time range for the current orbit.   
\*

-------- end definition ---

Current\_Sub\_Intv\_Id ( store )

= Natural.

The currently identified subinterval ID.

------- end definition --

Current\_Time ( data )

= Time. \* The current system time. \* - end definition -

Cycle\_Acct ( store ) = 0{ Num\_PCD\_Filled\_MJF + Num\_Avail\_ADP + Num\_Rejected\_ADP + Num\_Missing\_ADP + Num\_Avail\_EDP + Num\_Rejected\_EDP + Num\_Missing\_EDP + 1{ Num\_PCD\_MNF\_Sync\_Errors + Num\_PCD\_Filled\_MNF + Failed\_PCD\_Votes }128 }4. \* The buffer that contains the both minor and major frame accounting until the accounting for a complete PCD Cycle has been stored. \* - end definition ---

A Data Availability Notice (DAN) which is sent to the LPS DAAC to indicate the availability for transfer of the LPS output files associated with a particular contact period. It consists of information required by the LP-DAAC to transfer the files and then notify the LPS that files for that contact have been transferred. Potential information included is the LPS Host Name, address, a contact Id and a list of file names. \*

-------- end definition ---

DAN\_Suspended ( data )

= Boolean. \* This flag indicates whether DAN transfer is suspended. \* --- end definition ----

DAN\_Transfer\_State ( store , discrete )   
= [   
"ENABLED" |   
"DISABLED"   
].   
\*   
This flag controls whether to send DANs to the LP DAAC or not.   
\*   
- end definition --

DAN\_Transmission\_Time ( data )   
= Date +   
Time.   
\*   
This object represents time a DAN was transmitted from LPS to LP DAAC.   
\*   
------- end definition --------

Data\_Field\_Qual\_Indicator ( data , discrete )   
= [   
"UNCORRECTABLE" |   
"CORRECTABLE" |   
"NO\_ERRORS"   
].   
\*   
BCH checked data field quality for the associated CADU.   
\*   
- end definition -

Data\_Missing\_Message ( data ) = Message. \* Error message indicating that PCD Data is missing due to missing VCDUs. \* - end definition -

Date

( data , primitive )

= \* This item will contain a year, month and day of the month \* -------- end definition --------

Date\_Of\_Report\_Data ( data )

This object represents the date associated with the data in an LDTS file transfer summary report. \*

-------- end definition ---

Deinterleaved\_Band\_Data ( data )

= Format\_Id +   
[ Fmt1\_Band\_Data | Fmt2\_Band\_Data ]. \*   
All band data on a major frame basis that is deinterleaved   
according to band width. Data is reversed, if necessary.   
\* --- end definition -------

Direction\_Start

( data

Indicates the beginning of a forward or reverse scan. \*

--------- end definition -----

Directive

( data

= [ RDC\_Directive   
| RDP\_Directive   
| MFP\_Directive   
| IDP\_Directive   
| PCD\_Directive   
| LDT\_Directive   
| MACS\_Control\_Drct   
| MACS\_Modify\_Config\_Drct | MACS\_Modify\_Schedule\_Drct ]. Inputs from LPS personnel to control LPS operation or change LPS system setup parameters.   
\*

-------- end definition ---

Drift\_Rate

( data )

= 1{Bit}32.

The SV Time Drift Characterization Data used, along with the Time of Last SV Clock Update, to correct the spacecraft time, reported in the PCD and video, for clock drift. The drift rate is located in the first PCD Major Frame.PCD Minor Frame 36-39.Word 72 of each Full\_PCD\_Cycle.

---------- end definition ---------

## Drift\_Time

( data )

= Sub\_Intv\_Id + Drift\_Rate

A structure that contains the Sub\_Intv identification and the Drift\_Rate used to calculate the difference between the spacecraft time and the actual time of each ETM plus Major Frame on a Sub\_Intv basis.

-------- end definition ---

DTA

( data , primitive )

An unsolicited message from the LP DAAC indicating the status of the LP DAAC's attempt to transfer a set of LPS output files associated with a given contact ID. \*

-------- end definition --

DTA\_Time\_Of\_Receipt

( data

)

= Date + Time.

This object represents the time that a DTA from the LP DAAC for a contact ID was received by LPS.

-------- end definition -----

End\_Of\_Contact\_Flag

( data )

= Boolean.

Indicates whether the end of the contact period has been reached   
\* ----- end definition ---

Ending\_Row ( data )

= WRS\_Row\_Nominal.

The ending row of the last scene in a sub-interval. The information is determined by PCDS and is given to MACS for inclusion of metadata file via PCD\_Acct.

--------- end definition -----

Eol\_Thr ( data )

= Natural. \* The threshold value for the number of missing end of line code minor frames for a subinterval. \* -- end definition ---

EPA ( data )

= Real. \* Attitude estimate represented as an Euler Parameter. \* end definition -

EPA1

( data )

= EPA. \* First EPA of the quaternion defining rotation. \* - end definition -

EPA2 ( data )

= EPA. \* The second EPA of the quaternion defining the rotation. \* - end definition -

EPA3 ( data ) = EPA. \* The third EPA of the quaternion defining the rotation. \* - end definition -

EPA4 ( data ) = EPA. \* The fourth EPA of the quaternion defining the rotation. \* - end definition -

Ephem\_Position\_Lower ( data )

= Real. \* The smallest valid ephemeris position data point which is -8.3886x10^6 meters. \* - end definition -

Ephem\_Position\_Upper ( data ) = Real. \* The largest valid ephemeris position data point which is +8.3886x10^6 meters. \* -- end definition -

Ephem\_Position\_x ( data )= Real.\*The ephemeris/position x-coordinate value.\*- end definition -

Ephem\_Position\_y

( data )

= Real. \* The ephemeris/position y-coordinate value. \*

-------- end definition ---

Ephem\_Position\_z ( data )= Real.\*The ephemeris/position z-coordinate value.\*- end definition -

Ephem\_Velocity\_Lower ( data ) = Real. \* The smallest valid ephemeris data point value which is -8.0 meters./ms \* -- end definition --

Ephem\_Velocity\_Upper

( data )

= Real. \* The largest valid ephemeris data point value which is +8.0 meters/ms. \* - end definition -

Ephem\_Velocity\_x

( data )

= Real. \* The velocity x-coordinate. \*

-------- end definition --

Ephem\_Velocity\_y

( data )

= Real . \* The velocity y-coordinate value. \*

-------- end definition --

Ephem\_Velocity\_z ( data )

= Real.

The velocity z-coordinate value.

-------- end definition ----

## Ephemeris

( data )

= Ephem\_Velocity\_x

\+ Ephem\_Velocity\_y

\+ Ephem\_Velocity\_z

\+ Ephem\_Position\_x

\+ Ephem\_Position\_y

\+ Ephem\_Position\_z.

The position and velocity components of spacecraft at a specific time. The ephemeris data is located in PCD Major Frame 0 and 2.PCD Minor Frame 50-73.Word 72 or PCD Major Frame 1 and 3.PCD Minor Frame 16-39.Word 72. \*

-------- end definition ---

Est\_Time ( data )

= Real.

The estimated major frame time in 1/16th of a millisecond. \*

--------- end definition -----

Est\_Used\_Flag

( data )

= Boolean. \*

A true flag indicating that the actual major frame time was in error. The estimated time should be used. \*

------- end definition --

ETM\_Data\_Format

( data )

= Natural.

The ETM+ data format type provided by MFPS and is included in the metadata file.

-------- end definition ---

ETM\_Plus\_LOS\_x ( data )

= Real. \* The x-coordinate of the line of sight vector. \* - end definition ---

ETM\_Plus\_LOS\_y ( data )

= Real. \* The y-coordinate for the line of sight vector. \* - end definition --

ETM\_Plus\_LOS\_z ( data )

= Real. \* The z-coordinate for the line of sight vector. \* - end definition --

ETM\_Plus\_To\_Body\_Trans ( data )

= String. \* Parameters used to transform the longitude, latitude, sun elevation, and sun azimuth from ETM Plus to Spacecraft Body. \*

------- end definition ---

Exp\_Eol\_Ptr ( data )

= Ann\_VCDU. \*

The pointer to an annotated VCDU in which the end of line code minor frames are expected to be. \*

-------- end definition --

Exp\_Mnf\_Ctr ( data )

= Natural \*

The expected minor frame counter used for minor frame counter verification. \*.

Faild\_CADUs ( store )   
= {   
@Contact\_Id +   
Sync +   
[   
PN\_Decoded\_CADU\_Bytes |   
[   
VCDU\_Bytes |   
VCDU\_Hdr\_Bytes + VCDU\_Data   
] +   
VCDU\_Trailer   
] +   
Sync\_Annotation +   
(CRC\_Annotation) +   
(RS\_Annotation)   
}.   
\*   
The set of Grade 3 Failed CADUs and BCH Failed VCDUs for   
each data set processed by the RDPS and stored in such a   
way as to allow retrieval on a contact period basis.   
\*   
end definition -

-------- end definition ----

Exp\_VCDU\_Ctr ( data ) = Natural. \* The expected VCDU counter used for VCDU sequence counter verification. \* -------- end definition ---

Failed\_Mjf\_Data

A Major\_Frame\_VCDU\_Set that is missing either a major frame synchronization or both EOL code minor frames. This store is identified on

------- end definition ---

Failed\_PCD\_Votes ( store )

= Natural.

The number of failed attempts to perform a successful majority rule of three consecutive PCD information words (PCD\_Info\_Word). The majority vote is performed using the three consecutive words that follow the sync byte of each PCD data word cycle.

------- end definition --

Failed\_Votes

( store )

= Natural.

A buffer used to accumulate the number of unsuccessful attempts to perform a majority vote. The count is based on each PCD Minor Frame within a sub-interval. \*

-------- end definition ---

Failed\_Votes\_Message

( data )

= Message. \* Error message indicating the number of failed attempts to perform a majority vote to determine the PCD\_Info\_Word.

-------- end definition --

FHS\_Err

( data )

= 12{Char}12. \* The first half scan time error. \* - end definition -

File\_Location

( data )

= String. \*

Location of a file.

-------- end definition -----

File\_Version\_Number ( data )

= Natural. \* Description: A unique number assigned to the version of metadata file associated with a specific sub-interval, contact period. \* end definition --

Fill\_SCID ( data ) = 6{Bit}6. \* A SCID that contains all ones indicating a fill CADU. \* - end definition

Fill\_Value ( data )

First\_PCD\_MJF\_Time

( data

= Time. \* The Major\_Frame\_Time that corresponds to the spacecraft time of the first PCD Major Frame of a sub interval. \* -- end definition --

Flush\_Minor\_Frame

( data

= Contact\_Ended.

A flag used to indicate that all partially filled PCD Minor Frames should be completed using a predefined fill pattern due to the end of a contact period.   
\*

-------- end definition --

Fmt ( data )

= Natural. \* A value indicating whether the Mono, Multi1, Multi2 and

Multi3 band parameters are to be used for format 1 or 2 scene data: Format 1 = "0", Format 2 = "1" \* ---------- end definition ----------

Fmt1\_Align\_Data ( data ) = 0{ Fill\_Value }Max\_Alignment\_Value + Fmt1\_Band\_Data + 0{ Fill\_Value }Max\_Alignment\_Value. \* Format 1 aligned data. It includes bands 1 through 6. \* - end definition --

Fmt1\_Band\_Data ( data ) = 5{16{Band\_Det\_Data}16}5 + 4{Band6\_Det\_Data}4. \* Format 1 deinterleaved detector data. It includes bands 1 through 5 and band 6. \* -- end definition -

Fmt2\_Align\_Data ( data ) = 0{ Fill\_Value }Max\_Alignment\_Value + Fmt2\_Band\_Data + 0{ Fill\_Value }Max\_Alignment\_Value. \* Format 2 aligned data. It includes bands 6, 7, and Pan. The total sum of the fill values will equal the maximum alignment value. \* - end definition --

Fmt2\_Band\_Data ( data ) = 4{Band6\_Det\_Data}4 + 16{Band\_Det\_Data}16 + 2{32{Pan\_Det\_Data}32}2.

Format 2 deinterleaved detector data. It includes band 6,   
band 7, and Pan.   
\* - end definition --

Fmt\_Status

( data

= Message

Status indicating the success or failure of the validation of Band\_Parms.Fmt.   
\*

------- end definition --

Format\_Id

( data )

= Bit. \* Format 1/2 ID. Word 7 bit 4 of PCD/Status Data. Format 1 = "0", Format 2 = "1". \* - end definition -

Full\_Mjf\_Thr

( data )

= Natural. \* The threshold value for the number of full missing major frames occurring during a subinterval. \* -- end definition --

Full\_PCD\_Cycle

( store )

= Sub\_Intv\_Id + 4{PCD\_Major\_Frame}4. \* Consists of four PCD Major Frames whose Major Frame Id is sequentially numbered from 0-3. The full PCD cycle refers to a complete set of a PCD table of data. \* ----- end definition ---

Gain\_Change\_Flag

( data

, primitive )

"0" |   
"1"   
].   
\*   
A bit indicator of word 8 in the PCD/Status field. Low gain = "0". High gain = "1"   
\*   
- end definition

Gap\_Tagged\_VCDUs ( data ) = Mjf\_CADU\_Rcvd\_Cnt{ Ann\_VCDU + Num\_Missing\_VCDUs }Mjf\_CADU\_Rcvd\_Cnt. \* Contains an annotated VCDU and the number of missing VCDUs. \* - end definition ---

Grade\_3\_Chkd\_VCDU ( data )

= Contact\_Id + Sync + VCDU\_Hdr\_Bytes + VCDU\_Data + VCDU\_Trailer + Sync\_Annotation + CRC\_Annotation + RS\_Annotation.

A CADU that has completed the CCSDS Grade 3 processing and the data quality annotation from frame sync, CRC, and Reed-Solomon EDAC processes.

NOTE:

The contact ID is not part of the annotation, but simply shown as information necessary to associate this VCDU with a Contact\_Id.

-------- end definition ---

Gyro\_Data

( data

= Byte. \*

One byte of a 24 bit value, in two's complement with the most significant byte first, for each gyro axis in the PCD. The result of three orthogonal axes of the inertial measurement unit(IMU) which are sampled by the spacecraft

every 64 milliseconds.   
\*   
---------- end definition ----------

Horizontal\_Display\_Shift ( data )

The horizontal display shift of WRS scene. The information is determined by PCDS and is given to MACS for inclusion of metadata file via PCD\_Acct.   
\*

-------- end definition -----

IDP\_ACCA\_Status ( data )

= Message. \* This status reflects whether ACCA failed or succeeded. If ACCA failed, what type of failure \* - end definition --

IDP\_Acct ( store )

= {   
@Sub\_Intv\_Id +   
Browse\_File\_Names +   
Bands\_Present +   
Band\_File\_Names +   
PCD\_Scene\_Count +   
0{   
Band\_Gains +   
Gain\_Change\_Flag +   
(   
CCA\_Method +   
ACCA   
)   
}PCD\_Scene\_Count   
}.   
\*   
Information such as filenames, band numbers, sub-interval   
identifiers and sub-interval start and stop times for   
Browse, Band and ACCA tasks. There is multiple CCA information,   
one for each full scene if the format id is 1. There is no   
ACCA for format 2 data.   
\*   
-- end definition --

= (Mono) + (Multi1) + (Multi2) + (Multi3) + (Fmt) + (Subs) + (Wave) + (CCA\_Method) + (CCA\_Ratio) \*

( data

Operator-defined parameters specifying which bands to process for ACCA and Browse (Mono, Multi1, Multi2, Multi3), whether the band parameters are to be used for format 1 or 2 scene data (Fmt), and the reduction ratio to use   
when reducing browse image data by subsampling and by wavelets (Subs and Wave). CCA\_Method and CCA\_Ratio are two user-defined ACCA parameters.   
\*

-------- end definition -----

IDP\_Directive ( data )

= IDP\_Band\_Parms.

The directives and parameters sent to the IDPS from the MACS. \*

-------- end definition ----

IDP\_Setup\_Status

( data

= [ Mono\_Status | Multi1\_Status Multi2\_Status Multi3\_Status |

Fmt\_Status | Subs\_Status | Wave\_Status ].   
\* Status indicating the success or failure of the validation on monochrome and multi band parameters, the format ID, and the subsampling and wave ratios.   
\*

------- end definition --

IDP\_Status ( data )

= [ IDP\_Setup\_Status | IDP\_ACCA\_Status ]. \* Status messages sent from IDPS to the MACS \* - end definition -

Info\_Word

( data

= [ ADS | Gyro\_Data | Sync\_Word | Major\_Frame\_Id | Subcomm\_Word ]. \*

An eight-bit word that contains the mission-related telemetry describing the attitude, ephemeris, jitter, and other data that describes the status of the spacecraft and its subsystems.   
米

end definition

Info\_Word\_1

( data

= Info\_Word. \*

The first PCD information word that follows the PCD information word data cycle sync pattern.

Info\_Word\_2

( data )

= Info\_Word. \* The second information word that follows the PCD information word data cycle sync pattern. \*

-------- end definition ---

Info\_Word\_3

( data

= Info\_Word.

The third PCD information word that follows the PCD information word data cycle sync pattern.   
米

----- end definition --

Info\_Word\_Missing ( data )

= Natural. \* A value that indicates how many PCD data words are missing. \* - end definition --

Instrument\_Id

( data )

= Natural. \* The ETM+ instrument ID. \*

-------- end definition -----

Integer

( data

, primitive )

= \* An integer \* end definition -

Internal\_DAN

( data )

= Contact\_Id + Contact\_File\_Names.

This object contains all of the contact specific information required to generate a Data Availability Notice (DAN).   
\*

-------- end definition --

Inverted\_CADU\_Bytes ( data )

= 1036{Byte}1036

An inverted CADU extracted from the raw wideband data.

------- end definition --

Inverted\_Sync ( data ) = 4{Byte}4 \* Inverted Hex '1ACFFC1D \*. end definition

Lat\_And\_Long ( store ) = Sub\_Intv\_Id + Latitude + Longitude + Major\_Frame\_Time + Cal\_Door\_Activity\_Status. \* The calculated latitude and longitude for each PCD Major Frame. \* end definition --

= Real. \* The angular distance, measured in degrees, north or south from the equator.. \* -------- end definition -

= Message.

This flow will contain either an indication that a DAN was successfully sent (milestone) or that problems were detected while attempting to transmit a DAN. \*

LDT\_Delete\_Files\_Drct ( data )

= Contact\_Id \* DESCRIPTION: This control directive specifies a contact for which all LPS Output files are to be deleted. \* --- end definition --

LDT\_Delete\_Files\_Status ( data )

= Message. \* This is the contact ID associated with a set of files which have been deleted. \* end definition --

LDT\_Directive ( data )

= [ LDT\_Resend\_DAN\_Drct | LDT\_Retain\_Files\_Drct | LDT\_Rpt\_File\_Xfer\_Sum\_Drct | LDT\_Delete\_Files\_Drct | LDT\_Enable\_File\_Xfer\_Drct | LDT\_Disable\_File\_Xfer\_Drct

DESCRIPTION:   
The control directives from LPS personnel to control the LPS data transfer to LP DAAC.

\* - end definition -

LDT\_Disable\_File\_Xfer\_Drct ( data , primitive )

= \* A directive sent to LDTS for disabling the transfer of DAN to LP DAAC. \*

-------- end definition --

LDT\_DTA\_Status ( data )

This is a message which contains the contact ID associated with a set of LPS output files for which LPS has received a DTA from the LP DAAC. Also included is relevant transfer status information (e.g., success, failure, reason(s), etc.).

------- end definition ---

LDT\_Enable\_File\_Xfer\_Drct

( data

, primitive )

A directive sent to LDTS for enabling the transfer of DAN to LP DAAC.   
\*

-------- end definition ---

LDT\_Output\_File\_Info ( store ) = @Contact\_Id + DAN\_Suspended + Marked\_For\_Retention + Time\_Available + Time\_Deleted + {DAN\_Transmission\_Time } + {DTA\_Time\_Of\_Receipt } + Contact\_File\_Names.

This data store contains all state information about LPS output files that is of concern to LDTS.   
\*

-------- end definition ---

LDT\_Resend\_DAN\_Drct ( data )

= Contact\_Id

This directive is used to manually trigger LDTS to resend a DAN to the LP DAAC.   
\*

------- end definition ---

LDT\_Retain\_Files\_Drct ( data )

= Contact\_Id

This directive is used to retain the LPS files no matter what the file is successfully transferred to LP DAAC or not. The retained files will reside on the LPS indefinitely unless the operator deletes them manually using 'LPS\_File\_Deletion' directive. A contact schedule list menu will be prompted to the operator to choose which contact schedule files should be retained.   
\*

------- end definition ---

LDT\_Retain\_Files\_Status ( data )

= Message. \* This represents is a status message indicating the success or failure of the attempt to retain all files associated with a particular contact ID. \* -- end definition --

LDT\_Rpt\_File\_Xfer\_Sum\_Drct ( data )

= Date \* DESCRIPTION: This directive specifies a date for which a File Transfer Summary Report is to be generated. \* ---- end definition -

LDT\_Send\_DAN ( data )

= Contact\_Id + Contact\_File\_Names.

Indicates that all files for the contact have been generated and provides a list of completed LPS output filenames..   
\*

LDT\_Status ( data )

= [ LDT\_DAN\_Status | LDT\_DTA\_Status | LDT\_Retain\_Files\_Status | LDT\_Delete\_Files\_Status   
] \*

LGS\_Channel\_Id ( data )

= String.

The identifier for an LGS connection used by an LPS string.

------- end definition --

Longitude ( data )

= Real. \* Distance east or west on the earth's surface, measured as an arc of the equator between the meridian passing through a particular place and standard meridian. \* --- end definition ---

Lower\_Left\_Corner\_Latitude ( data )

= Real \* WRS scene lower left corner latitude. The angular distance, measured in degrees, north or south from the equator. \* -- end definition -

Lower\_Left\_Corner\_Longitude ( data )

WRS scene lower left corner longitude. Distance east or west on the earth's surface, measured as an arc of the equator between the meridian passing through a particular place and standard meridian. \*

-------- end definition -----

Lower\_Right\_Corner\_Latitude ( data )

= Real \* WRS lower right corner latitude. The angular distance, measured in degrees, north or south from the equator. \* - end definition --

Lower\_Right\_Corner\_Longitude ( data )

= Real \* WRS lower right corner longitude. Distance east or west on the earth's surface, measured as an arc of the equator between the meridian passing through a particular place and standard meridian. \* ----- end definition --------

<table><tr><td>LPS_Acct</td><td>(store</td><td>）</td></tr><tr><td>= RDC_Acct +</td></tr><tr><td>RDP_Acct +</td></tr><tr><td></td></tr><tr><td>MFP_Acct + PCD_Acct +</td></tr></table>

The LPS quality and accounting information created by LPS subsystems. The

information is used to construct the Metadata\_File on a subinterval basis. The quality and accounting files are retrieved by the MACS once MACS receives the Sub\_Intv information from the MFPS.   
\*

-------- end definition ---

LPS\_Configuration ( store )

= LPS\_Hardware\_String\_Id + LGS\_Channel\_Id + LPS\_Software\_Version\_Number + Spacecraft\_Id + Instrument\_Id + File\_Version\_Number.

The setup information used to startup LPS.

-------- end definition -----

LPS\_File\_Transfer\_Status ( data , primitive )

This string will indicate the success or failure of an attempt by the LP DAAC to transfer LPS output files from LPS to the LP DAAC.

------- end definition --

This includes all L0R files generated by LPS.   
\*.

-------- end definition ---

LPS\_Hardware\_String\_Id ( data )

Description:

The data string number configured by LGS/LPS personnel. It is configured in the LPS\_Configuration store.

------- end definition --

LPS\_Journal ( store )

= { [ RDC\_Status | RDP\_Status | MFP\_Status | PCD\_Status | IDP\_Status | MACS\_Directive\_Dispatch\_Status |

MACS\_Metadata\_Generation\_Status | MACS\_Control\_Status |   
MACS\_Modify\_Schedule\_Status | MACS\_Modify\_Config\_Status |   
LDT\_Status   
]   
}.   
\*   
A system log file containing all activities which occurred   
during LPS operation   
\*

## LPS\_Report

( data

[ Report\_RDC\_Data\_Capture\_Sum | Report\_RDP\_Return\_Link\_QA | Report\_MFP\_L0R\_QA | Report\_LDT\_File\_Xfer\_Sum ].

The processing summary information generated by the RDCS, RDPS, and LDTS, respectively. These summary information serves as LPS processing   
monitoring media by LPS personnel. The information is sent by the subsystem by either contact period basis, or by daily basis.   
\*

------ end definition --

LPS\_Software\_Version\_Number ( data ) = Natural. \* A unique number assigned to specific LPS software version. \* --- end definition --

LPS\_Status ( data ) = [ MACS\_Directive\_Dispatch\_Status | MACS\_Metadata\_Generation\_Status | MACS\_Control\_Status | MACS\_Modify\_Config\_Status | MACS\_Modify\_Schedule\_Status | RDC\_Status | RDP\_Status | MFP\_Status | PCD\_Status | IDP\_Status | LDT\_Status ]. \* The status information used to monitor LPS processing. \* end definition -

MACS\_Control\_Drct ( data , discrete ) = [ "Startup" | "Shutdown" ] \* A method of controlling LPS system activities. \* --- end definition -

MACS\_Control\_Status ( data )

MACS\_Directive\_Dispatch\_Status ( data , discrete ) = [ "SUCCESS" | "FAIL" ]. \* The directive dispatching status. \* end definition -

MACS\_Metadata\_Generation\_Status ( data ) = Message. \* Messages indicating the results of the metadata file generation process. \* --------- end definition ----------

MACS\_Modify\_Config\_Drct ( data ) = (LPS\_Hardware\_String\_Id) + (LGS\_Channel\_Id) + (LPS\_Software\_Version\_Number) + (Spacecraft\_Id) + (Instrument\_Id) + (File\_Version\_Number). \* A LPS configuration modification directive keyed by LPS personnel to replace the existing LPS\_Configuration. \* -- end definition -

MACS\_Modify\_Config\_Status ( data )

= Message. \* A text string containing error information. \* - end definition -

MACS\_Modify\_Schedule\_Drct ( data ) = (Contact\_Schedule\_Id) + Modification\_Type + Contact\_Schedule\_Start\_Time + Contact\_Schedule\_Stop\_Time. \*

A contact schedule modification directive to update an existing contact schedule, to insert a new contact schedule or to delete an existing contact schedule.   
\*

-------- end definition ---

MACS\_Modify\_Schedule\_Status ( data )

= Message.

A text string containing error information.

-------- end definition --

Maj\_Vote\_Tol ( data )

= Natural

A value indicating the minimum number of identical bits that are required for the data word group majority vote.   
\*.

-------- end definition --

Major\_Frame\_Acct ( data )

= Num\_PCD\_Filled\_MJF + Num\_Avail\_ADP + Num\_Rejected\_ADP + Num\_Missing\_ADP + Num\_Avail\_EDP + Num\_Rejected\_EDP + Num\_Missing\_EDP. \*

PCD Major Frame related statistics.

-------- end definition --

Major\_Frame\_Id ( data ) = Byte. \* Unique identifier, from 0 to 3, which indicates the position of the PCD Major Frame within the PCD Cycle. \* end definition

Major\_Frame\_Time ( data )

= Actual\_Time + (Est\_Time) + Est\_Used\_Flag. \* The time associated with one major frame. This time is extracted from minor frames two through seven. It is calculated according to the minor frame format as stated in the DFCB. \*

------- end definition --

Major\_Frame\_VCDU\_Set ( data ) = Gap\_Tagged\_VCDUs + Exp\_Eol\_Ptr + Mjf\_CADU\_Seq\_Err\_Cnt + Mjf\_CADU\_Fly\_Cnt + Mjf\_CADU\_Rcvd\_Cnt + Mnf\_Ctr\_Err. \*

Structure with a pointer to a set of VCDUs for one scan bit value, that is, one major frame's worth of data.

------ end definition --

Majority\_Vote\_Failure ( data ) = Bit. \* A flag indicating a failure or a success when performing a majority vote to determine the PCD\_Info\_Word. \* -------- end definition -----

Marked\_For\_Retention ( data , discrete ) = [ "RETAIN" | "DELETE" ]. \* A flag indicating whether LPS will automatically delete all files associated with a contact. \* - end definition -

Max\_Alignment\_Value ( data ) = Natural.

The maximum value allowable as an alignment value.

------- end definition --

Message

( data , primitive )

= \* The messages used to monitor LPS processing. This will contain information such as the message ID, a time tag, and optional string messages \*

-------- end definition -----

## Metadata\_File

= Metadata\_Header + Mjf\_CADU\_BER\_Cnt + Mjf\_CADU\_Sync\_Err\_Cnt + Mjf\_CADU\_Rcvd\_Cnt + Mjf\_CADU\_Missing\_Cnt +

VCDU\_Hdr\_Err\_Count +   
Mjf\_CADU\_BCH\_Corr\_Cnt +   
Mjf\_CADU\_BCH\_Uncorr\_Cnt +   
Mjf\_CADU\_BCH\_Bits\_Corr +   
Mjf\_Full\_Fill\_Cnt +   
Mjf\_Part\_Fill\_Cnt +   
Mjf\_Time\_Code\_Err\_Cnt +   
Failed\_PCD\_Votes +   
Num\_PCD\_MNF\_Sync\_Errors +   
Num\_PCD\_Filled\_MNF +   
Num\_PCD\_Filled\_MJF +   
Num\_Avail\_ADP +   
Num\_Rejected\_ADP +   
Num\_Missing\_ADP +   
Num\_Avail\_EDP +   
Num\_Rejected\_EDP +   
Num\_Missing\_EDP +   
0{   
Sub\_Intv\_Scene\_Num +   
WRS\_Path\_Nominal +   
WRS\_Row\_Nominal +   
Scene\_Center\_Time +   
Scene\_Center\_Scan\_Num +   
Horizontal\_Display\_Shift +   
Center\_Latitude +   
Center\_Longitude +   
Upper\_Left\_Corner\_Latitude +   
Upper\_Left\_Corner\_Longitude +   
Upper\_Right\_Corner\_Latitude +   
Upper\_Right\_Corner\_Longitude +   
Lower\_Left\_Corner\_Latitude +   
Lower\_Left\_Corner\_Longitude +   
Lower\_Right\_Corner\_Latitude +   
Lower\_Right\_Corner\_Longitude +   
Sun\_Azimuth +   
Sun\_Elevation +   
CCA\_Quadrant1\_Score + CCA\_Quadrant2\_Score + CCA\_Quadrant3\_Score + CCA\_Quadrant4\_Score + CCA\_Aggregate\_Score +   
Gain\_Change\_Flag +   
Band\_Gains   
}PCD\_Scene\_Count.   
A file containing information on the Level OR processing   
for a specific subinterval.   
\* -------- end definition --

Metadata\_File\_Name ( data ) = File\_Location + "L7\_" + MF\_Start\_Time + " + Metadata\_File\_Type + + File\_Version\_Number. \* The metadata file name. \* - end definition

Metadata\_File\_Type ( data , discrete )

= "Metadata". \* A string identifying the Metadata file. \* - end definition -

Metadata\_Header

( data

= Current\_Time + File\_Version\_Number + LPS\_Hardware\_String\_Id + LPS\_Software\_Version\_Number + Spacecraft\_Id + ETM\_Data\_Format +

Instrument\_Id +   
Contact\_Start\_Time + Orbit\_Num +   
MF\_Start\_Time +   
MF\_Stop\_Time +   
Mjf\_Count +   
Num\_PCD\_MJF +   
First\_PCD\_MJF\_Time + WRS\_Path\_Nominal + Starting\_Row +   
Ending\_Row +   
PCD\_File\_Name +   
Browse\_File\_Names + Cal\_File\_Name +   
MSCD\_File\_Name +   
Band\_File\_Names +   
Bands\_Present +   
ETM\_Data\_Format. The overall accounting information associated with a subinterval data.   
Browse\_File\_Names are only for data format type 1.

MF\_Start\_Time

( data

= Major\_Frame\_Time. \* Subinterval start time. \* - end definition -

MF\_Stop\_Time

( data )

= Major\_Frame\_Time. \* Subinterval stop time. \* - end definition --

MFP\_Acct

( store

= { @Sub\_Intv\_Id + Mjf\_VCDU\_QA + Cal\_File\_Name +

MSCD\_File\_Name }.   
\*

All quality and accounting information that is received on

a major frame basis for a given subinterval. It consists of   
information on the major frame processing data, the   
Calibration filename and MSCD filename.   
\* ------ end definition --------

MFP\_Cal\_Status

( data

= Message \* Status messages as a result of processing the calibration data \* end definition -

MFP\_Directive ( data ) = [ MFP\_Rpt\_L0R\_QA\_Drct | MFP\_Parms | MFP\_Thresholds ]. \* Description: The directive sent to MFPS to control the MFPS subsystem . \* - end definition --

MFP\_Mjf\_Status

( data

= Message \* Threshold error messages from MFPS. end definition -

MFP\_MSCD\_Status

( data

MFP\_Parms

( store

= (Sensor\_Alignment\_Info) + (Fill\_Value) +

(Sub\_Intv\_Delta) +   
(Mjf\_Data\_Rate) +   
(Max\_Alignment\_Value) + (Time\_Range\_Tol) +   
(Part\_Mnf\_Tol) +   
(Maj\_Vote\_Tol).   
\*

The MFPS setup parameters.

------ end definition --

MFP\_Rpt\_L0R\_QA\_Drct ( data )

= Sub\_Intv\_Id.

Upon receipt of this control directive from LPS personnel, the MFPS will gather the Level 0R quality and accounting information for   
the specified sub-interval and forward the information to the   
MACS for either display or hardcopy report.   
\*

------- end definition ---

MFP\_Setup\_Status

( data

= Message \*

A return status to indicate acceptance or rejection of operator controls.

MFP\_Status

( data

= [ MFP\_Setup\_Status | MFP\_Mjf\_Status | MFP\_Cal\_Status | MFP\_MSCD\_Status ]. \*

Status messages sent to MACS from the MFPS.

MFP\_Thresholds

( store

= (Mjf\_CADU\_Seq\_Err\_Thr) + (Scan\_Dir\_Thr) + (Sync\_Thr) + (Mnf\_Ctr\_Thr) +

(Eol\_Thr) +   
(Tc\_Thr) +   
(Full\_Mjf\_Thr) +   
(Part\_Mjf\_Thr).   
\*   
The MFPS threshold values. \*   
end definition

Minor\_Frame\_Acct ( data )

= Num\_PCD\_MNF\_Sync\_Errors + Num\_PCD\_Filled\_MNF + Failed\_PCD\_Votes.

Statistics gathered from the building of the PCD Minor Frames.

------- end definition --

Mission\_Start\_Time ( data )

= Time. \* The start time of the Landsat Mission. \* end definition --

Mjf\_CADU\_BCH\_Bits\_Corr ( data )

= Natural. \* The total number of bits that were BCH corrected in the mission data zone of a CADU on a subinterval basis \* - end definition -

Mjf\_CADU\_BCH\_Corr\_Cnt ( data ) = Natural. \* The number of CADUS with BCH errors corrected in the mission data zone per major frame. \* -- end definition -

Mjf\_CADU\_BCH\_Uncorr\_Cnt ( data )

= Natural.

The number of CADUS with BCH errors in the mission data zone uncorrected per major frame.   
\*

------- end definition --

Mjf\_CADU\_BER\_Cnt ( data )

= Natural.

The BER (based on BCH and/or CRC detected bit errors) in the mission data zone on a subinterval basis. \*

-------- end definition --

Mjf\_CADU\_Bit\_Slip ( data )

= Natural. \* Indicates the bit slip total for the currently accumulated major frame set. \* - end definition -

Mjf\_CADU\_CRC\_Err\_Cnt

( data )

= Natural \* The count of CADUs with CRC errors.

------- end definition --

Mjf\_CADU\_Fly\_Cnt

( data )

The count of flywheel CADUs for a subinterval.

-------- end definition --

Mjf\_CADU\_Missing\_Cnt

( data )

= Natural. \* Number of missing CADUs per major frame. \* end definition --

Mjf\_CADU\_Polarity ( data )

= Natural.

The CADU synchronization information polarity for the currently accumulated set of major frames. \*

-------- end definition ---

Mjf\_CADU\_Rcvd\_Cnt ( data )

= Natural.

The count of received CADUs per subinterval.

-------- end definition --

Mjf\_CADU\_RS\_Corr\_Cnt ( data )

= Natural. \* The number of correctable VCDU headers per major frame. \* - end definition -

Mjf\_CADU\_RS\_Uncorr\_Cnt ( data )

= Natural.

The number of uncorrectable VCDU headers per major frame. \*

-------- end definition --

Mjf\_CADU\_Seq\_Err\_Cnt ( data )

= Natural.

The number of VCDU counter errors in a major frame.

-------- end definition --

Mjf\_CADU\_Seq\_Err\_Thr ( data )

= Natural \*

Threshold value for the number of VCDU sequence counter errors that occur in a subinterval.

\*. end definition -

Mjf\_CADU\_Sync\_Err\_Cnt ( data )

= Natural.

The count of CADUs with synchronization errors for a major frame.

-------- end definition --

Mjf\_CADU\_Sync\_Info ( data )

= Mjf\_CADU\_Polarity + Mjf\_CADU\_Sync\_Strategy + Mjf\_CADU\_Bit\_Slip.

The synchronization information including the polarity, the synchronization strategy and the number of bit slips for a subinterval.   
\*

--------- end definition -----

Mjf\_CADU\_Sync\_Strategy ( data )

= Valid\_CCSDS\_Parms.

The CADU synchronization strategy setup parameters on a subinterval basis.   
\*

-------- end definition --

Mjf\_Count

( data )

= Natural. \* The total number of major frames on a subinterval basis. \* - end definition -

Mjf\_Data\_Rate

( data )

The nominal data rate of major frames per millisecond. \*

-------- end definition --

Mjf\_Eol\_Err\_Cnt ( data ) = Natural. \* The number of end of line errors encountered on a subinterval basis. \* -- end definition --------

Mjf\_Full\_Fill\_Cnt ( data )

= Natural. \* The number of major frames that need to be fully filled for a subinterval. \* -- end definition -

Mjf\_Part\_Fill\_Cnt ( data )

= Natural. \* The number of major frames that need to be partially filled for a subinterval. \* ---- end definition --

Mjf\_QA ( data ) = Mjf\_Count + Mjf\_Tossed\_Cnt + Mjf\_Eol\_Err\_Cnt + Mnf\_Ctr\_Err. \* The major frame quality and accounting information calculated on a subinterval basis. \* - end definition -

MJF\_Time\_And\_Position ( store )   
= Sub\_Intv\_Id +   
{   
@Major\_Frame\_Time +   
Attitude +   
Ephemeris +   
Cal\_Door\_Activity\_Status   
}.   
\*

The position and time of each PCD Major Frame within a   
sub-interval.   
\* ------ end definition --------

Mjf\_Time\_Code\_Err\_Cnt ( store )

= Natural. \* The count of imagery time code errors on a subinterval basis. \* - end definition --

Mjf\_Tossed\_Cnt ( data )

The number of major frames that are calculated from the   
sync errors and the end of line code errors on a subinterval   
basis.   
\* - end definition --

= Mjf\_QA + VCDU\_QA + Mjf\_Full\_Fill\_Cnt + Mjf\_Time\_Code\_Err\_Cnt.

Quality and accounting information totals for the currently processed Major Frames and VCDUs in a particular subinterval. \*

Mjf\_VCDU\_Data ( data ) = Gap\_Tagged\_VCDUs + Direction\_Start. \* Contains the annotated VCDUs and any VCDUs with gaps tagged. The start of either a forward or reverse scan is contained in the direction start. \* - end definition ----

Mjf\_VCDU\_Parms ( data )

= Maj\_Vote\_Tol + Part\_Mnf\_Tol + Mjf\_Data\_Rate + Time\_Range\_Tol + Sub\_Intv\_Delta. \* MFPS Parameters used during the parsing of the major frames. \* - end definition

Mjf\_VCDU\_QA ( store ) = VCDU\_QA + Mjf\_QA + Mjf\_Time\_Code\_Err\_Cnt + Mjf\_Full\_Fill\_Cnt + Mjf\_Part\_Fill\_Cnt. \* Currently calculated quality and accounting information accumulated for CADUs and major frames on a subinterval basis. \* end definition -----

Mjf\_VCDU\_QA\_Report\_Info ( data ) = Mjf\_Count + Mjf\_CADU\_Sync\_Info + Mjf\_CADU\_Sync\_Err\_Cnt + Mjf\_CADU\_Rcvd\_Cnt + Mjf\_CADU\_Fly\_Cnt + Mjf\_CADU\_Missing\_Cnt + Mjf\_CADU\_RS\_Corr\_Cnt + Mjf\_CADU\_RS\_Uncorr\_Cnt + Mjf\_CADU\_BCH\_Corr\_Cnt + Mjf\_CADU\_BCH\_Uncorr\_Cnt + Mjf\_CADU\_CRC\_Err\_Cnt + Mjf\_Full\_Fill\_Cnt + Mjf\_Part\_Fill\_Cnt + Mjf\_CADU\_BER\_Cnt. \* The Level 0R quality and accounting data needed to generate the Level 0R quality and accounting report on a subinterval basis. \* end definition ---------

Mnf\_Ctr\_Err ( data ) = Natural.

The number of minor frame counter errors in a major frame   
on a subinterval basis.   
\* ------ end definition --------

Mnf\_Ctr\_Thr ( data )

= Natural \* Threshold value for the number of minor frame counter errors that in a subinterval. \*. ----- end definition ---------

Modification\_Type ( data , discrete ) = [ "INSERT" | "UPDATE" | "DELETE" ]. \* Description: A database store modification type. \*

Mono

( data

= Integer

Image data for one predetermined band that has been reduced by subsampling. It also contains the sub-interval start and

stop times, the subinterval identifier and the subsampling   
and wavelet reduction ratios.   
\* ----- end definition ----

Mono\_Band\_Wave ( data ) = Mono\_Wave\_Image + MF\_Start\_Time + MF\_Stop\_Time + Sub\_Intv\_Id + Subs + Wave. \* Image data from one predetermined band that has been reduced first by subsampling and next by wavelets. It also contains the subinterval start and stop times, the subinterval identifier, and the subsampling and wavelet reduction ratios. \* - end definition

Mono\_Browse\_File\_Name ( data ) = File\_Location + "L7\_" + MF\_Start\_Time + + Mono\_Browse\_File\_Type + " + File\_Version\_Number. \* Name of monochrome browse file. \* - end definition -

Mono\_Browse\_File\_Type ( data , discrete )

= "Mono". \* A string identifying the monochrome browse file. \* - end definition -

Mono\_Status ( data ) = Message. \* Status indicating the success or failure of the validation of monochrome band parameter.

\* - end definition ---------

Mono\_Subs\_Image

= {Pixel}.   
\*   
Image data for one predetermined band that has been reduced   
by subsampling. \* --- end definition ----

Mono\_Wave\_Image ( data )

Image data from one predetermined band that has been reduced first by subsampling and next by wavelets. \*

------- end definition --

MSCD\_Data

( store

= { Scan\_Dir + SHS\_Err + FHS\_Err }. \*

The mirror scan correction data collected for the MSCD\_File on a major frame basis for a given subinterval. The MSCD data is located immediately following the End of line code pattern and is extracted from 2 contiguous minor frames.

-------- end definition -----

= { Scan\_Dir + SHS\_Err + FHS\_Err   
}. \*

A file containing the Scan Line data extracted from the two minor frames following the End of Line Code in each major frame for a given subinterval.

------- end definition ---

MSCD\_File\_Name MSCD\_File\_Name ( data (data )

= File\_Location + "L7\_" + MF\_Start\_Time + + MSCD\_File\_Type + " + File\_Version\_Number. \* The mirror scan correction file name. \* end definition --

MSCD\_File\_Type ( data , discrete )

= "MSCD". \* A string identifying the MSCD file. \* - end definition -

Multi1

( data )

= Integer

A band parameter that specifies the first of three bands to process for Browse and ACCA.

-------- end definition --

Multi1\_Status

( data )

= Message. \*

Status indicating the success or failure of the validation of the multiband 1 band parameter.   
\*

------ end definition --

Multi2

( data )

= Integer

A band parameter that specifies the second of three bands

to process for Browse and ACCA.

------ end definition ---

Multi2\_Status ( data )

= Message. \*

Status indicating the success or failure of the validation of the multiband 2 band parameter.   
\*

------- end definition --

Multi3 ( data )

= Integer

A band parameter that specifies the third of three bands to process for Browse and ACCA.

\* - end definition

Multi3\_Status

( data )

= Message.

Status indicating the success or failure of the validation of the multiband 3 band parameter.   
\*

-------- end definition -----

Multi\_Band\_Subs

( data )

= Multi\_Subs\_Image + MF\_Start\_Time +   
MF\_Stop\_Time + Sub\_Intv\_Id + Subs + Wave. \*

Image data from three predetermined bands that has been reduced by subsampling. It also contains the subinterval start and stop times, the subinterval identifier, and the subsampling and wavelet reduction ratios. \*

------- end definition --

Multi\_Band\_Wave ( data ) = Multi\_Wave\_Image + MF\_Start\_Time + MF\_Stop\_Time + Sub\_Intv\_Id + Subs + Wave. \* Image data from three predetermined band that has been reduced first by subsampling and next by wavelets. It also contains the subinterval start and stop times, the subinterval identifier, and the subsampling and wavelet reduction ratios. \* -- end definition -----

Multi\_Browse\_File\_Name ( data ) = File\_Location + "L7\_" + MF\_Start\_Time + + Multi\_Browse\_File\_Type + " + File\_Version\_Number. \* Name of multiband browse file. \* end definition

Multi\_Browse\_File\_Type ( data , discrete ) = "Multi". \* A string identifying the multiband browse file. \* -- end definition --------

Multi\_Subs\_Image

( data )

= {Pixel}. \*   
Image data from three predetermined bands that has been reduced by subsampling. \* - end definition -

Multi\_Wave\_Image ( data ) = {Pixel}. \* Image data from three predetermined band that has been reduced first by subsampling and next by wavelets. \* - end definition -

MUX\_Id ( data )

= Bit \* Multiplexer (MUX) assembly ID. Word 7 bits 1-3 of PCD/Status Data. \* --- end definition --

Natural ( data , primitive )

= \* The range 0-MAXINT. \* - end definition

Nominal\_Scene\_Coords ( data ) = Sub\_Intv\_Id + PCD\_Scene\_Count + Sub\_Intv\_Scene\_Num + WRS\_Row\_Nominal + WRS\_Path\_Nominal + Scene\_Center\_Time + Scene\_Center\_Scan\_Num + Cal\_Door\_Activity\_Status. \* The parameters describing the nominal position for each WRS scene. \* ------ end definition ---

Num\_Avail\_ADP ( data )

= Natural. \* The number of attitude data points that are available on a sub interval basis. \* - end definition -

Num\_Avail\_EDP ( data )

= Natural. \* The number of ephemeris data points that are available on a sub interval basis. \* - end definition --

Num\_Failed\_Votes ( data )

= Integer.

The threshold for reporting errors when unsuccessful majority votes are performed.   
\*

------- end definition --

Num\_Missing\_ADP ( data )

= Natural.\*

The number of attitude data points that are not available for a PCD Major Frame on a sub interval basis. \*

-------- end definition ---

Num\_Missing\_Data\_Words ( data )

= Integer.

The threshold for reporting errors when PCD Information Words are missing due to missing VCDUs.

-------- end definition -----

Num\_Missing\_EDP ( data )

= Natural.\*

The number of ephemeris data points that are not available for a PCD Major Frame on a sub interval basis.

-------- end definition --

Num\_Missing\_VCDUs ( data )

= Natural. \* The number of missing VCDUs prior to the current VCDU. \* - end definition ---

Num\_PCD\_Filled\_MJF ( data )

= Natural.\*

The number of PCD Major Frames that contain fill values for a sub interval.

-------- end definition --

Num\_PCD\_Filled\_MNF ( data )

= Natural.

The number PCD Minor Frames that contain predefined fill values on a sub interval basis.   
\*

-------- end definition --

Num\_PCD\_MJF ( data )

= Natural.\*The number of PCD Major Frames per sub interval.\*- end definition --

Num\_PCD\_MNF\_Sync\_Errors ( data )

= Natural.\*

The number of missing PCD Minor Frame sync words per sub interval.

-------- end definition --

Num\_Rejected\_ADP ( data ) = Natural. \* The number of attitude data points that were determined invalid on a sub interval basis. \* - end definition ---

Num\_Rejected\_EDP ( data )

= Natural.

The number of ephemeris data points that were determined invalid on a sub interval basis.   
\*

-------- end definition --

Online\_Browse\_File\_Count ( data )

= Natural \* Count of online browse files. \* end definition

Online\_L0R\_File\_Count ( data )

Count of online L0R files.

-------- end definition ---

Online\_LPS\_File\_Names

( data )

= { Contact\_File\_Names }.

The names of LPS output files which are available for transfer to the LP DAAC and for which a DAN has been sent. \*

------- end definition ---

Online\_Metadata\_Count ( data )

= Natural

Count of online metadata files.

-------- end definition ---

Orbit\_Num ( data )

= Natural.

\*   
The current revolution/orbit count.   
\* ---------- end definition ---------

Orbit\_Time ( data ) = Time. \* Orbit upper time range. \* - end definition -

Overlay\_Marks ( data ) = {Scene\_Id + Pixel\_Index }. \* Identifies the pixels in Mono\_Band\_Wave and Multi\_Band\_Wave which contain a scene center id. \* end definition

Overlay\_Subs ( data ) = Overlay\_Marks + MF\_Start\_Time + MF\_Stop\_Time + Sub\_Intv\_Id + Subs + Wave. \* Specifies the overlay tick marks for the data in Mono\_Band\_Subs and Multi\_Band\_Subs. \*

Overlay\_Wave ( data ) = Overlay\_Marks + MF\_Start\_Time + MF\_Stop\_Time + Sub\_Intv\_Id + Subs + Wave. \*

Specifies the overlay tick marks for the data in Mono\_Band\_Wave and Multi\_Band\_Wave. \* -- end definition -----

Pan\_Det\_Data ( data ) = 6313{Byte}6313. \* Aligned detectors for pan data. \* - end definition -

Part\_Mjf\_Thr

( data )

= Natural. \* The threshold value for the number of partially filled major frames in a subinterval. \* end definition -

Part\_Mnf\_Tol

( data )

Partial\_PCD\_Cycle

( store )

= 1{PCD\_Major\_Frame}3. \* A buffer which contains the PCD Major Frames that will be used to build the Full\_PCD\_Cycle. \* - end definition --

Partial\_PCD\_Major\_Frame

( store )

= 1{PCD\_Minor\_Frame}128. \* A buffer that contains >=1<128 PCD Minor Frames. \* --- end definition ------

Partial\_PCD\_Minor\_Frame ( store )

= 1{Info\_Word}128.

A buffer that contains >=1<128 PCD information words.

-------- end definition ---

Partial\_Rep\_Info\_Word ( store )

= Info\_Word\_1

\+ Info\_Word\_2

\+ Info\_Word\_3.

Buffer for information words that have not been declared as Rep\_Info\_Words.   
\*

------ end definition --

PCD\_Acct ( store ) = { @Sub\_Intv\_Id + PCD\_File\_Name + Num\_PCD\_MJF + First\_PCD\_MJF\_Time + Orbit\_Num + 4{ Minor\_Frame\_Acct + Major\_Frame\_Acct }4 + PCD\_Scene\_Count + 0{ Sub\_Intv\_Scene\_Num + WRS\_Path\_Nominal + WRS\_Row\_Nominal + Scene\_Center\_Time + Scene\_Center\_Scan\_Num + Horizontal\_Display\_Shift + Sun\_Azimuth + Sun\_Elevation + Cal\_Door\_Activity\_Status }PCD\_Scene\_Count }. \*

A file that contains the statistics that are gathered from the processing of PCD bytes, the building of PCD Minor and Major Frames, and the extraction and interpretation of information from the PCD Major Frames. The PCD\_Acct file is maintained on a subinterval basis.

\* end definition ---

PCD\_Assemble\_Cycle\_Status ( data ) = [ Data\_Missing\_Message | Failed\_Votes\_Message ]. \* Errors that are detected during the processing of PCD data. \*

PCD\_Bytes ( data ) = 4{Byte}4. \* The four bytes that are extracted from the PCD/Status field of the VCDU. \* -------- end definition ----

PCD\_Directive

( data

= [ PCD\_Parms | PCD\_Thresholds   
]. \* The parameters used by the PCDS during the subsystem initialization process. The parameters are maintained in the PCDS.   
\*

PCD\_File ( store )

= {Qualified\_PCD\_Cycle}.   
\* A file containing the PCD major frames received during a subinterval on a full PCD cycle basis. A PCD cycle consists of four PCD major frames. \* - end definition ----

PCD\_File\_Info

( data

= Sub\_Intv\_Id +

PCD\_File\_Name +   
Num\_PCD\_MJF +   
First\_PCD\_MJF\_Time + Orbit\_Num.   
\*

PCD\_File related data that identifies the file and describes the contents of the file.

------- end definition ---

PCD\_File\_Name ( data ) = File\_Location + "L7\_" + MF\_Start\_Time + \_" + PCD\_File\_Type + " + File\_Version\_Number. \* The PCD file name. \* - end definition

= "PCD". \* PCD File identifier string. \* end definition

PCD\_Frame\_Fill ( data ) = Byte. \* Predefined value that is stored used to fill missing PCD data when building PCD Minor and Major Frames. \* -- end definition -

PCD\_Frame\_Info = Sub\_Intv\_Id + 4{ Minor\_Frame\_Acct + Major\_Frame\_Acct }4.

( store

The statistics that are gathered from the processing of PCD bytes and the building of the PCD Major and Minor Frames. Information is gathered on a full PCD cycle basis.

-------- end definition --

PCD\_Info ( data ) = Sub\_Intv\_Id + PCD\_Bytes + End\_Of\_Contact\_Flag + Num\_Missing\_VCDUs. \* The information needed by the PCDS. \* - end definition -

PCD\_Info\_Word ( data )

= Sub\_Intv\_Id + Info\_Word + Flush\_Minor\_Frame + Info\_Word\_Missing + Majority\_Vote\_Failure.

The information word that will be used to build the PCD Minor Frame(s).

-------- end definition ---

PCD\_Major\_Frame ( data ) = 128{PCD\_Minor\_Frame}128. \* A structure that contains 128 PCD Minor Frames. \* ---------- end definition ---------

PCD\_Minor\_Frame ( data )

= 128{Info\_Word}128. \* A structure that contains 128 PCD information words. \* - end definition --

PCD\_Parms ( data )

= (ETM\_Plus\_To\_Body\_Trans) +   
(Mission\_Start\_Time) +   
(Time\_Per\_Orbit) +   
(ETM\_Plus\_LOS\_x) +   
(ETM\_Plus\_LOS\_y) +   
(ETM\_Plus\_LOS\_z) +   
(Semi\_Major\_Axis) +   
(Semi\_Minor\_Axis) +   
(PCD\_Frame\_Fill) +   
(   
WRS\_Row\_Nominal +   
Latitude +   
{   
WRS\_Path\_Nominal +   
Longitude   
}   
).   
\*   
PCD Parameters used in processing PCD data including:   
Parameters that are provided by the IAS and used to   
calculate the longitude and latitude, the WRS Scene Id,   
and sun elevation and azimuth, and   
The Worldwide Reference System parameters containing the   
information for one WRS row.   
\*

-------- end definition ---

PCD\_Scene\_Count

( store )

= Natural.

The number of WRS scenes that have been identified within a sub-interval.   
\*

-------- end definition ---------

PCD\_Setup\_Status

( data )

= Message.

An error message containing a list of the invalid PCD parameters and thresholds and their values.   
\*

--------- end definition -----

PCD\_Status

( data )

= [

PCD\_Setup\_Status |

PCD\_Assemble\_Cycle\_Status   
].   
\*   
Status messages sent from the PCDS to the MACS.   
\* ------ end definition -------

PCD\_Thresholds ( data ) = (Ephem\_Position\_Upper) + (Ephem\_Position\_Lower) + (Ephem\_Velocity\_Upper) + (Ephem\_Velocity\_Lower) + (Att\_Lower\_Bounds) + (Att\_Upper\_Bounds) + (Num\_Missing\_Data\_Words) + (Num\_Failed\_Votes). \* PCD threshold parameters used in processing PCD data. \* - end definition

= Byte \* A byte of image data \*. - end definition --

Pixel\_Index ( data ) = Integer. \* Specifies the index into Mono\_Subs\_Image and Multi\_Subs\_Image pixel image. \* - end definition -

PN\_Decoded\_CADU\_Bytes ( data ) = 1036{Byte}1036. \* The bytes of a CADU that have been PN decoded. \* -- end definition --

Polarity\_Unknown\_Bytes ( data ) = 1036{Byte}1036 \* A stream of bytes from the raw wideband data that has not been checked for polarity \* -------- end definition --------

Polarity\_Unknown\_Sync ( data )

= [ Sync | Inverted\_Sync   
] \*   
A sync marker that has not been checked for polarity   
\* ------- end definition --------

Prev\_VCID ( data = VCID \* The VCID of the previous VCDU \* end definition --

Previous\_Lat\_And\_Long ( store )

= Lat\_And\_Long. \*

Latitude and longitude values that were previously checked against the latitude and longitude values in the WRS scheme. The latitude and longitude values are retained to confirm WRS scene center crossing and for use in interpolating the actual scene center latitude and longitude. \*

-------- end definition ---

Qualified\_PCD\_Cycle

( data )

= Full\_PCD\_Cycle.

A Full\_PCD\_Cycle that has been time checked and determined to be part of the current sub interval.

------- end definition ---

Raw\_Data\_Byte\_Stream ( data ) = {Byte}. \* Byte stream for a single LPS string containing Raw\_WB\_Data. \* -- end definition ---

Raw\_WB\_Sets ( store ) = { @Contact\_Id + Raw\_Data\_Byte\_Stream }. \* This store contains the Raw\_WB\_Data to be processed. \* -- end definition --

= Natural.

Approximate number of scenes in Raw\_WB\_Data set (Rcv\_Dat\_Vol\_Mbytes / Mbytes per scene).

Rcv\_Dat\_Vol\_Mbytes

= Natural. \* Data volume in megabytes derived from the difference between the Contact\_Start\_Time and the Contact\_Stop\_Time divided by number of megabytes per second. \* - end definition ---

RDC\_Acct ( store ) = { @Contact\_Id + Rcv\_Dat\_Vol\_Mbytes }. \* Raw Data Capture accounting information. \* - end definition

RDC\_Capture\_Drct ( data , discrete ) = [ "START" | "STOP" ]. \* The directive sent by MACS used to control LPS raw data capture process \* ------- end definition --

RDC\_Capture\_Stat

( data )

= Message. \*

A message returned to MACS stating the disposition of capture of raw wideband data and a Contact\_Id following received MACS directive or a warning message stating that the datastore already contains three contact periods. \*

--------- end definition -----

RDC\_Delete\_Drct

( data )

= Contact\_Id.

The directive sent by MACS used to delete the Raw\_WB\_Data file for the contact period requested.   
\*

------- end definition --

RDC\_Delete\_Stat

( data )

= Message. \* A message stating the deletion of the Raw\_WB\_Data file is complete. \* ---- end definition ---

RDC\_Directive

( data )

= [ RDC\_Capture\_Drct | RDC\_Delete\_Drct | RDC\_Save\_Drct | RDC\_Restage\_Drct |

RDC\_Rpt\_Data\_Capture\_Sum\_Drct   
].   
\*   
DESCRIPTION:   
The control directives from LPS personnel to guide the LPS data capture processing.   
\*   
--------- end definition --

RDC\_Restage\_Drct ( data )

= Contact\_Id +   
[ "START" | "STOP"   
]. \*

The directive sent by MACS used to control the restaging of the raw wideband data from the 60-day store process. \*

-------- end definition ---

RDC\_Restage\_Stat ( data )

= Message. \* A message stating the restaging of a raw wideband data set (Raw\_WB\_Data) is complete. \* - end definition ------

RDC\_Rpt\_Data\_Capture\_Sum\_Drct ( data )

= Contact\_Id

DESCRIPTION:

Upon receipt of this control directive from LPS personnel, the RDCS will gather the Landsat 7 raw data capture summary information for the operator specified contact period and forward the information to the MACS for either display or hardcopy report. This directive is used by an event basis.

------- end definition --

RDC\_Save\_Drct ( data )

= Contact\_Id + [

"START" |   
"STOP"   
].   
\*   
The directive sent by MACS used to start the LPS raw data save to removable media containing the Contact\_Id needed to identify the data set.   
\*   
-- end definition --

RDC\_Save\_Stat ( data )

= Message. \* A message sent to the MACS stating the saving of raw wideband data is complete. \* - end definition -

RDC\_Status ( data ) = [ RDC\_Capture\_Stat | RDC\_Delete\_Stat | RDC\_Save\_Stat | RDC\_Restage\_Stat ]. \* Status messages returned from the RDCS \* - end definition -

= { @Contact\_Id + Valid\_CCSDS\_Parms + CADU\_Polarity + CADU\_Bit\_Slip + CADU\_Sync\_Error\_Count + CADU\_Rcv\_Count + CADU\_Flywheel\_Count + CADU\_Missing\_Count + CADU\_CRC\_Error\_Count + VCDU\_Header\_Correctable\_Error\_Count + VCDU\_Header\_Uncorrectable\_Error\_Count + BCH\_Data\_Corrected\_Error\_Count + BCH\_Pointer\_Corrected\_Error\_Count + BCH\_Data\_Uncorrected\_Error\_Count + BCH\_Pointer\_Uncorrected\_Error\_Count + BER

Aggregate information summarizing the CCSDS Grade 3 quality of a raw wide band data set.   
\*

RDP\_BCH\_Err\_Status ( data )

= Message \* Status message stating BCH errors exceed threshold. \* - end definition --

RDP\_BER\_Err\_Status ( data )

= Message. \* Status message stating that the maximum bit error rate has been exceeded. \* --- end definition -----

RDP\_CCSDS\_Parms ( data ) = (CADU\_Search\_Tolerance) + (CADU\_Check\_Tolerance) + (CADU\_Flywheel\_Tolerance) + (CADU\_Sync\_Marker\_Check\_Error\_Tolerance) + (CADU\_Sync\_Lock\_Error\_Tolerance) + (CADU\_Bit\_Slip\_Correction\_Extent). \* Parameters that control CCSDS frame synchronization and bit slip correction. \* -- end definition --------

RDP\_CRC\_Err\_Status ( data )

= Message \* Status message stating that the CRC error threshold has been exceeded \* -- end definition --

RDP\_Directive ( data )

= [ RDP\_Process\_Drct | RDP\_Rpt\_Return\_Link\_QA\_Drct | RDP\_Thresholds | RDP\_CCSDS\_Parms ]. \* DESCRIPTION: The control directives from LPS personnel to guide Landsat 7 raw data processing. \* ---------- end definition --------

RDP\_Process\_Drct ( data )

= Contact\_Id. \*   
Notification to the RDPS to begin processing The contact channel information for processing the raw wideband data. \* - end definition --

RDP\_Rpt\_Return\_Link\_QA\_Drct ( data )

= Contact\_Id. \* This directive requests a return link summary report for a given contact period. \*

------- end definition --

RDP\_RS\_Err\_Status ( data ) = Message \* Status message indicating that the maximum number of Reed\_Solomon errors has been exceeded. \* - end definition --

RDP\_Setup\_Status ( data ) = Message \* An error message containing a list of the invalid CCSDS parameters and RDP thresholds and their values \* -------- end definition ----------

RDP\_Status ( data ) = [ RDP\_Setup\_Status | RDP\_Sync\_Err\_Status | RDP\_CRC\_Err\_Status | RDP\_RS\_Err\_Status | RDP\_BCH\_Err\_Status | RDP\_BER\_Err\_Status ]. \* Status messages returned from the RDPS \* - end definition

RDP\_Sync\_Err\_Status ( data )

= Message \* Status message indicating that the error threshold for sync errors has been exceeded. \* ---------- end definition ----------

RDP\_Thresholds ( data ) = (Sync\_Thres) + (CRC\_Thres) + (RS\_Thres) + (BCH\_Thres) + (BER\_Thres).

RDP processing thresholds sent from the MACS.   
\* ----- end definition --

Real ( data (data = \* Real number. \*. end definition -

, primitive )

Rel\_VCDU\_Cnt = Natural. \*

At any time the current number of VCDUs in Ann\_VCDU\_Collection.   
\* ---------- end definition ----------

Removable\_Media ( store ) = { @Contact\_Id + Raw\_Data\_Byte\_Stream }. \* The collection of raw wideband data sets stored on removable media. \* --- end definition -

Rep\_Info\_Word ( data ) = Sub\_Intv\_Id + Info\_Word\_1 + Info\_Word\_2 + Info\_Word\_3 + Info\_Word\_Missing + Contact\_Ended. \* A structure that contains the PCD\_Info\_Word in triplicate and the PCD Information Word status. \* - end definition --

Report\_LDT\_File\_Xfer\_Sum ( data ) = Current\_Time + Date\_Of\_Report\_Data + Available\_LPS\_File\_Names + Available\_L0R\_File\_Count + Available\_Browse\_File\_Count + Available\_Metadata\_Count + Online\_LPS\_File\_Names + Online\_L0R\_File\_Count + Online\_Browse\_File\_Count + Online\_Metadata\_Count + Transmitted\_LPS\_File\_Names + Volume\_Of\_Retained\_Data + Available\_Retention\_Space.

A report containing the count of LPS files available, the count of LPS files retained online, the count of LPS files transmitted to the LP DAAC, and the usage and

availability of data output store. \* ---------- end definition ----------

Report\_MFP\_L0R\_QA ( data ) = Mjf\_VCDU\_QA\_Report\_Info + MF\_Start\_Time + MF\_Stop\_Time. \* The Level 0R quality and accounting report per subinterval. \* ------ end definition ----

Report\_RDC\_Data\_Capture\_Sum ( data ) = Contact\_Id + Rcv\_Dat\_L7\_Scenes + Rcv\_Dat\_Vol\_Mbytes. \* Aggregate accounting information for a single channel for a single contact period. \* -- end definition ---

Report\_RDP\_Return\_Link\_QA ( data )

= LPS\_Hardware\_String\_Id + Contact\_Start\_Time + Contact\_Stop\_Time + CADU\_Polarity + CADU\_Bit\_Slip + CADU\_Sync\_Error\_Count + CADU\_Rcv\_Count + CADU\_Flywheel\_Count + CADU\_Missing\_Count + VCDU\_Header\_Correctable\_Error\_Count + VCDU\_Header\_Uncorrectable\_Error\_Count + BCH\_Data\_Corrected\_Error\_Count + BCH\_Pointer\_Corrected\_Error\_Count + BCH\_Data\_Uncorrected\_Error\_Count + BCH\_Pointer\_Uncorrected\_Error\_Count + CADU\_CRC\_Error\_Count + Approx\_Data\_Received + Approx\_Major\_Frame\_Count + Approx\_ETM\_Count +   
BER.

A report containing the RDP\_Acct data store's entries for

a specified raw wideband data set (Raw\_WB\_Data).

------- end definition --

RS\_Acct

( data )

= Contact\_Id + VCDU\_Header\_Correctable\_Error\_Count + VCDU\_Header\_Uncorrectable\_Error\_Count. \*

The counts of the correctable and uncorrectable header errors determined during the Reed-Solomon error detection and correction.

--------- end definition -----

RS\_Annotation

( data )

= Boolean. \* An indication of the quality of the associated CADU based on the Reed-Solomon EDAC checks. \* - end definition --

RS\_Corr\_CADU

( data )

= Contact\_Id + Sync +   
[ VCDU\_Hdr\_Bytes | VCDU\_Fill\_Hdr\_Bytes   
] + VCDU\_Data + VCDU\_Trailer + Sync\_Annotation + CRC\_Annotation + RS\_Annotation

A CADU that has completed the Reed\_Solomon EDAC and the data quality indicators from the frame sync CRC and Reed\_Solomon processes.

NOTE:   
The contact ID is not part of the annotation, but simply shown as information necessary to associate this CADU with a Contact\_Id.   
\*

-------- end definition -----

RS\_Failed\_CADU ( data )

= CRC\_Chkd\_CADU.

This is a CADU which has failed the Reed-Solomon checks. \*

-------- end definition --

RS\_Thres

( data )

= Natural \* The maximum number of Reed\_Solomon errors allowed before notifying the operator. \*

-------- end definition --

Saved\_Time

( store

= Actual\_Time.

The storage for the most recent actual major frame time.

Saved\_VCID

( store

= [ Prev\_VCID | Curr\_VCID ]. \*

The VCID which is checked for a changed value \*

-------- end definition ---

Scan\_Dir

( data

-------- end definition ---

Scan\_Dir\_Thr ( data ) = Natural. \* Threshold value for the number of Failed\_Mjf\_VCDU\_Set. \* - end definition --

Scene\_Center\_Scan\_Num ( data )

= Natural.   
\* The scan count, within a sub-interval, of the WRS scene center. \* end definition --

Scene\_Center\_Time ( data ) = Time. \* Description: The WRS scene center time when the image was taken. The information is determined by PCDS and is given to MACS for inclusion of metadata file via PCD\_Acct. \*

Scene\_Data ( data ) = {Pixel}. \* Data for a full scene, all bands for format 1 \* - end definition

Scene\_Data\_Store ( store ) = { Aligned\_Bands + Scene\_Data }. \* Storage where aligned bands accumulates until a full scene has been collected. \* - end definition -

Scene\_Id

( store

= WRS\_Row\_Nominal + WRS\_Path\_Nominal + Sun\_Elevation + Scene\_Center\_Time.

The position, time and sun elevation for each WRS scene.

-------- end definition ---

Scene\_Info

( data )

= PCD\_Scene\_Count + PCD\_Scene\_Count{ Scene\_Id }PCD\_Scene\_Count. \*

A structure that contains the scene identification and the parameters used to calculate the scene id for each identified scene. The scene identification is in accordance with the Worldwide Reference System (WRS) scheme. \*

-------- end definition ---

Scene\_Metadata

( data

= Sub\_Intv\_Id + Scene\_Id \*

Uniquely identifies a scene by using the sub-interval from which the data came and the scene id itself. \*

end definition

Scene\_Parms

( store

= Sub\_Intv\_Id +   
PCD\_Scene\_Count + 0{ Sub\_Intv\_Scene\_Num + WRS\_Path\_Nominal +   
WRS\_Row\_Nominal +   
Scene\_Center\_Time +   
Scene\_Center\_Scan\_Num +   
Horizontal\_Display\_Shift +   
Sun\_Azimuth +   
Sun\_Elevation +   
Cal\_Door\_Activity\_Status Input parameters used to determine the scene id, and the intermediate values derived from the scene id calculation. There is one entry for each Scene.   
\*

-------- end definition --

SCID ( data ) = 8{Bit}8. \* Spacecraft ID as it comes in the raw wideband data. \* - end definition

= Real. \* The distance from Apogee or Perigee to the center of the orbit ellipse = R(Apogee) + R(Perigee)/2. \* - end definition -

Semi\_Minor\_Axis ( data )= Real.\*Polar axis radius.\*- end definition

Sensor\_Alignment\_Info ( data ) = 4{Natural}4. \* Information provided by IAS and used by the MFPS to perform integer-pixel alignment. \* - end definition --

SHS\_Err ( data ) = 12{ Char }12. \* The second half scan time error.

\* - end definition --------

Shtr

= Bit. \* Shtr 1/2. Word 7 bit 6 of PCD/Status Data. Cal Shtr = "0", Backup Shtr = "1". \* - end definition -

Spacecraft\_Id

( data

= Natural. \* Landsat 7 spacecraft ID. \* -- end definition ---

Starting\_Row

( data

= WRS\_Row\_Nominal.

The beginning row of the first scene in a sub-interval. The information is determined by PCDS and is given to MACS for inclusion of metadata file via PCD\_Acct. \*

------- end definition --

= MUX\_Id + Shtr + Format\_Id + Band\_Num + Band\_Gains + Gain\_Change\_Flag.

The status information extracted from the PCD/Status field of the VCDU. Word 7 and 8 of the PCD/Status Data. \*

-------- end definition ---

String = {Char}. \*

An array of characters \* --- end definition --------

Sub\_Intv

( store

= { Contact\_Id + { @Sub\_Intv\_Id + MF\_Start\_Time + MF\_Stop\_Time + VCID }   
}. \*

The beginning and ending major frame times corresponding to

a predefined subinterval time range for each contact.

Sub\_Intv\_Delta ( store ) = Real. \* Time in milliseconds. The Sub\_Intv\_Delta value after validation. \* end definition

( data

= Metadata\_File\_Name + PCD\_File\_Name + Browse\_File\_Names + Cal\_File\_Name + MSCD\_File\_Name + Band\_File\_Names

A list of the specific file names associated with a subinterval.

Sub\_Intv\_Id ( data )

The subinterval's id used to determine the subinterval.

\* end definition ---

Sub\_Intv\_Info

( data

= Contact\_Id + VCID + VCID\_Change\_Flag + End\_Of\_Contact\_Flag.

The flags are needed for subinterval determination. The IDs are needed for the subinterval structure. \*

-------- end definition ---

Sub\_Intv\_Scene\_Num ( data )

= Natural.

A scene identifier representing the number of scenes identified thus far in a Sub\_Intv.   
\*

------- end definition --

Subcomm\_Word

( data )

= Byte. \*

Word 72 of all PCD minor frames. Contains data essential to the ground segment image processing such as Ground Reference, spacecraft id and various temperatures. \*

end definition

Subs

( data )

A reduction ratio to be used when subsampling browse image data. Specifies the size square grid to reduce to one   
pixel.   
\*

------- end definition ---

Subs\_Status

( data )

= Message.

Status indicating the success or failure of the validation   
of subsampling ratio band parameter.   
\* ------ end definition --------

Sun\_Azimuth ( data )= Real.\*Solar angle.\*- end definition -

Sun\_Elevation ( data )= Real.\*Solar elevation.\*- end definition --

Sync ( data ) = 4{Byte}4 \* Hex '1ACFFC1D' \*. end definition

Sync\_Annotation ( data ) = CADU\_Polarity\_Flag + CADU\_Bit\_Slip + CADU\_Sync\_Error\_Flag + CADU\_Flywheel\_Flag + End\_Of\_Contact\_Flag. \* The data quality indicators from the frame synchronization process and a flag to indicate if the end of the contact period has been reached. \* - end definition --

Sync\_Loc ( data )

= Natural \* The location of the frame sync marker relative to the start of the data \* end definition ---

Sync\_Thr ( data )

= Natural

-------- end definition ---

Sync\_Thres ( data )

= Natural.

The maximum number of sync errors allowed before notifying the operator

-------- end definition ---

Sync\_WB\_Data

( data

= Contact\_Id +   
Sync\_Loc + 0{Bit}8 + Polarity\_Unknown\_Sync + Polarity\_Unknown\_Bytes + 0{Bit}7 + Sync\_Annotation.

The raw wideband data bytes that have not been checked for polarity, along with the location of the sync marker and the sync annotations.

NOTE:   
The contact ID is not part of the annotation, but simply shown as information necessary to associate this CADU with a Contact\_Id.   
\*

-------- end definition -----

Sync\_Word ( data )

= Byte. \*

Sync pattern, xFAF320, which will appear in words 0 through 2 of each PCD minor frame.

------- end definition ---

Tc\_Thr ( data ) = Natural \* The threshold value for the number of time code errors occurring in a subinterval . \*. - end definition -

Time ( data , discrete ) = [ "YYYY DDD HH:MM:SS.mmm.nnn.uuu" | "DDD HH:MM:SS.mmm" | "time\_t" | "TBD" ]. \* LPS time formats. \* - end definition -

Time\_Available ( data ) = Date + Time. \* This object represents the time that the output files associated with a particular contact ID were made available for transfer. \* -- end definition --------

Time\_Code ( data ) = {Byte}. \* The VCDUs containing the time code minor frames. \* - end definition

Time\_Deleted ( data ) = Date + Time. \* This object represents the time that the output files associated with a particular contact ID were deleted. \*

-------- end definition ---

Time\_Per\_Orbit ( data ) = Time. \* The amount of time required for Landsat to make one complete orbit. \* ---- end definition --

Time\_Range\_Tol ( data )

= Real.

Time in 1/16th of a millisecond. The time range from system time backwards to system time minus the Time\_Range\_Tol.   
\*

-------- end definition --

Transfer\_Request ( data , primitive ) = \* This object represents a list of LPS output files the LP DAAC is requesting from LPS. \*. -- end definition --

Transmitted\_LPS\_File\_Names ( data ) = { Contact\_File\_Names }. \* The names of LPS output files which have been transmitted to the LP DAAC. \* - end definition -

Upper\_Left\_Corner\_Latitude ( data ) = Real \* WRS scene upper left corner latitude. The angular distance, measured in degrees, north or south from the equator. \* --- end definition --------

Upper\_Left\_Corner\_Longitude ( data )

= Real

WRS scene upper left corner longitude. Distance east or west on the earth's surface, measured as an arc of the equator between the meridian passing through a particular place and standard meridian.   
米

-------- end definition --

Upper\_Right\_Corner\_Latitude ( data )

= Real

WRS scene upper right corner latitude. The angular distance, measured in degrees, north or south from the equator.

-------- end definition ---

Upper\_Right\_Corner\_Longitude ( data )

= Real

WRS scene upper right corner longitude. Distance east or west on the earth's surface, measured as an arc of the equator between the meridian passing through a particular place and standard meridian.

--------- end definition -----

Valid\_Band\_Parms ( store )

= Mono + Multi1 + Multi2 + Multi3 + Subs + Wave + CCA\_Method + CCA\_Ratio. \*

A datastore containing four validated band parameters entered by an operator that specify which bands to process for ACCA and Browse. Valid band numbers are 1-6. The Mono parameter is for monochrome browse data; Multi1, Multi2, and Multi3 are for multiband browse

data. Subs and Wave are subsampling and wavelet   
reduction ratios, respectively. CCA\_Method and CCA\_Ratio   
are two user-defined ACCA parameters.   
\* ---------- end definition ---------

Valid\_CCSDS\_Parms ( store ) = CADU\_Search\_Tolerance + CADU\_Check\_Tolerance + CADU\_Flywheel\_Tolerance + CADU\_Sync\_Marker\_Check\_Error\_Tolerance + CADU\_Sync\_Lock\_Error\_Tolerance + CADU\_Bit\_Slip\_Correction\_Extent. \* Validated CCSDS parameters. \* end definition ---

Valid\_MFP\_Parms ( store ) = Sensor\_Alignment\_Info + Fill\_Value + Sub\_Intv\_Delta + Mjf\_Data\_Rate + Max\_Alignment\_Value + Time\_Range\_Tol + Part\_Mnf\_Tol + Maj\_Vote\_Tol. \* The validated MFPS setup parameters. \* end definition -

Valid\_MFP\_Thres ( store )   
= Mjf\_CADU\_Seq\_Err\_Thr +   
Scan\_Dir\_Thr +   
Sync\_Thr +   
Mnf\_Ctr\_Thr +   
Eol\_Thr +   
Tc\_Thr +   
Full\_Mjf\_Thr +   
Part\_Mjf\_Thr.   
\*   
The validated MFPS threshold values.   
\*   
end definition -

Valid\_PCD\_Parms ( store ) = PCD\_Frame\_Fill. \* The validated PCD Parameters used in processing PCD data. \* -- end definition --

Valid\_PCD\_Thres ( store ) = Ephem\_Position\_Upper + Ephem\_Position\_Lower + Ephem\_Velocity\_Upper + Ephem\_Velocity\_Lower + Att\_Lower\_Bounds + Att\_Upper\_Bounds + Num\_Missing\_Data\_Words + Num\_Failed\_Votes. \* The validated PCD threshold parameters used in processing PCD data. \* - end definition -

Valid\_RDP\_Thres ( store ) = Sync\_Thres + CRC\_Thres + RS\_Thres + BCH\_Thres + BER\_Thres \* Validated RDP processing thresholds \* end definition

Valid\_Scene\_Parms ( store )   
= ETM\_Plus\_To\_Body\_Trans +   
Mission\_Start\_Time +   
Time\_Per\_Orbit +   
Semi\_Major\_Axis +   
Semi\_Minor\_Axis +   
ETM\_Plus\_LOS\_x +   
ETM\_Plus\_LOS\_y +   
ETM\_Plus\_LOS\_z.   
\*   
The validated general mission information and parameters   
that are provided by the IAS and used to calculate the   
longitude and latitude, the WRS Scene Id, and sun elevation   
and azimuth.

-------- end definition --

Valid\_WRS\_Parms ( store ) = { @WRS\_Row\_Nominal + @WRS\_Path\_Nominal + Center\_Latitude + Center\_Longitude + Upper\_Left\_Corner\_Latitude + Upper\_Left\_Corner\_Longitude + Upper\_Right\_Corner\_Latitude + Upper\_Right\_Corner\_Longitude + Lower\_Left\_Corner\_Latitude + Lower\_Left\_Corner\_Longitude + Lower\_Right\_Corner\_Latitude + Lower\_Right\_Corner\_Longitude }. \* The validated Worldwide Reference System table containing the information for each WRS scene. \* -------- end definition -- end definition

VCDU\_Bytes ( data ) = 1034{Byte}1034. \* The bytes of a VCDU minus the trailer. \* - end definition

VCDU\_Corrected\_Mission\_Data ( data ) = 7936{Bit}7936. \* The mission data field of the VCDU with 1 to 3 bits BCH corrected \* - end definition -

VCDU\_Data ( data ) = VCDU\_Mission\_Data + 272{Bit}272. \* A VCDU with an uncorrected mission data zone. \* - end definition

VCDU\_Fill\_Hdr\_Bytes ( data ) = Bit + Fill\_SCID + 54{Bit}54. \* The header portion of a VCDU with a SCID that indicates fill data. \* - end definition

VCDU\_Hdr\_Bytes ( data )

= Bit + SCID + 54{Bit}54. \* The header portion of a VCDU. \* - end definition -

VCDU\_Hdr\_Err\_Count ( data ) = Mjf\_CADU\_RS\_Corr\_Cnt + Mjf\_CADU\_RS\_Uncorr\_Cnt. \* The total number of VCDU header error control errors (Reed-Solomon). \* --- end definition -

VCDU\_Hdr\_Fmt1\_Correctable\_Err\_Cnt ( data ) = Natural. \* Count of correctable VCDU headers for format 1. \* -- end definition ---------

VCDU\_Hdr\_Fmt2\_Correctable\_Err\_Cnt ( data )

= Natural. \* Count of correctable VCDU headers for format 2. \* end definition --

VCDU\_Header\_Correctable\_Error\_Count ( data ) = VCDU\_Hdr\_Fmt1\_Correctable\_Err\_Cnt + VCDU\_Hdr\_Fmt2\_Correctable\_Err\_Cnt. \* Count of correctable VCDU headers by VCID. \* ---------- end definition --------

VCDU\_Header\_Uncorrectable\_Error\_Count ( data ) = Natural. \* Number of uncorrectable errored VCDUs. \* ---- end definition --------

VCDU\_Mission\_Data ( data ) = 7936{Bit}7936. \* The mission data field of the VCDU with no corrections applied. \* end definition --

VCDU\_QA ( data ) = Mjf\_CADU\_Rcvd\_Cnt + Mjf\_CADU\_Fly\_Cnt + Mjf\_CADU\_Sync\_Info + Mjf\_CADU\_Sync\_Err\_Cnt + Mjf\_CADU\_Missing\_Cnt + Mjf\_CADU\_RS\_Corr\_Cnt + Mjf\_CADU\_RS\_Uncorr\_Cnt + Mjf\_CADU\_BCH\_Corr\_Cnt + Mjf\_CADU\_BCH\_Uncorr\_Cnt + Mjf\_CADU\_BCH\_Bits\_Corr + Mjf\_CADU\_CRC\_Err\_Cnt + Mjf\_CADU\_BER\_Cnt + Mjf\_CADU\_Seq\_Err\_Cnt + ETM\_Data\_Format. \* Currently calculated quality and accounting informatio accumulated for CADUs on a subinterval basis. \* - end definition -

VCDU\_Trailer ( data )

= 2{Byte}2. \* The bytes of a VCDU trailer. \* - end definition -

VCDU\_With\_Fill\_Info ( data )

= Ann\_VCDU + Num\_Missing\_VCDUs. \* A VCDU structure containing the pointer to the VCDU and the number of missing VCDUs that were expected before this VCDU. \* - end definition --

VCID ( data )

= 6{Bit}6. \* The virtual channel Id number. \* - end definition -

VCID\_Change\_Flag ( data ) = Boolean. \* Flag indicating whether the VCID has changed \* - end definition -

Volume\_Of\_Retained\_Data ( data )= Natural.\*

This object represents the number of units of volume of disk space which are currently being used for LPS output files retained on-line.   
\*

-------- end definition --

Wave ( data )

= Natural. \* A ratio to be used when reducing browse image data by wavelets. Specifies the size square grid to reduce to one

pixel.   
\* end definition ---

Wave\_Status

( data )

= Message. \*

Status indicating the success or failure of the validation of wavelet ratio band parameter.   
\*

-------- end definition ---

WRS\_Path\_Nominal

( data )

= Natural.

Standard designator for a nominal scene center. The WRS Path is the east to west index of the WRS Table. \*

-------- end definition ---

WRS\_Row\_Nominal

( data )

= Natural. \* Standard designator for a nominal scene center. The WRS Row is the north to south index of the WRS Table. \*

-------- end definition ---

## Appendix C - WRS Scene Identification Algorithms

This appendix describes and analyzes a WRS scene identification algorithm intended for implementation in the Landsat Processing System (LPS). The appendix provides the following information.

• A summary of the algorithm's input data and their sources.

A description of the algorithm.

• An analysis of the algorithm's computational complexity.

An estimate of the Delivered Source Instructions (DSIs) required to implement the algorithm.

Table C-1 PCD Items Needed for WRS Scene Identification
<table><tr><td rowspan=2 colspan=1>Data</td><td rowspan=1 colspan=2>Location</td></tr><tr><td rowspan=1 colspan=1>MajorFrame</td><td rowspan=1 colspan=1>MinorFrame</td></tr><tr><td rowspan=4 colspan=1>Euler Parameters</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>0 - 15</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>0 - 15</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>0 - 15</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>0 - 15</td></tr><tr><td rowspan=4 colspan=1>Spacecraft Position</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>50 - 61</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>16 - 27</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>50 - 61</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>16 - 27</td></tr><tr><td rowspan=2 colspan=1>Spacecraft Time</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>28 - 34</td></tr><tr><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>96 - 102</td></tr></table>

Table C-2 IAS Data Items Needed for WRS Scene Identification
<table><tr><td>Earth semimajor axis</td></tr><tr><td>Earth semiminor axis</td></tr><tr><td>Transformation matrix from ETM+ line of sight at</td></tr><tr><td>center of scan to spacecraft body ETM+ line of sight vector at center of mirror scan</td></tr></table>

The problem to be addressed is this. Given a continuous sequence of (validated and possibly corrected) 3-tuples containing spacecraft time, attitude, and ephemeris, provide the following information for each WRS scene contained within the sub-interval.

• The scene's WRS path and row.

The scene center time, i.e. the time code of the major frame containing the datum nearest the nominal WRS scene center position.

The scene center scan number, i.e. the index (beginning at 1) within the sub-interval's sequence of major frames of the major frame containing the datum nearest the nominal scene center.

• The nominal latitudes and longitudes for the WRS scene center and four corners.

The Sun azimuth and elevation at the ground point viewed by the datum nearest the nominal WRS scene center position.

The horizontal display shift, i.e. the distance (in TBD units of measure) between the ground point viewed by the datum nearest the nominal WRS scene center position and the nominal WRS scene center position.

Briefly stated, the algorithm below computes a position (latitude/longitude) of the ground point being viewed for each attitude/ephemeris pair extracted from the PCD. Each position and its predecessor is used to determine whether the spacecraft passed over a WRS scene center between the two positions (see figure 1). The algorithm uses a look-up table (WRS\_LUT) that contains, among other things, the nominal scene center position for each WRS scene. If so, the algorithm interpolates to compute the "actual" scene center's time and position. Because Landsat 7's track is not identical to a track along the WRS scene path, there can be some distance between the nominal scene center and any ground point observed on the track. The actual scene center is then that ground point closest to the nominal scene center defined by the WRS.

Figure C-1 Spacecraft view points bracketing a nominal scene  
![](images/57f8e1c8ffed3492d478c4368ba7dc7eb0d9f6acd2e8879b29b263e7e1144ecc.jpg)

The detailed description of the algorithm presented below is divided into three parts. Algorithm #1, "WRS Scene Identification," describes the top-level algorithm for identifying a WRS scene. Separate descriptions are provided for the following components of the algorithm.

Computing the latitude/longitude of a ground point. This is described in the Latitude and Longitude Computation.

Computing the Sun azimuth and elevation at a ground point at a given time. This is described in the white paper, Sun Azimuth and Elevation Algorithms, January 23, 1995.

Computing the Geocentric Inertial (GCI) sun vector for a given position at a given time. This computation is required by the Sun azimth and elevation algorithm. It is described in the white paper, Sun Azimuth and Elevation Algorithms, January 23, 1995.

Computing the Greenwich Hour Angle (GHA) for a given position at a given time. This is described in the white paper, Sun Azimuth and Elevation Algorithms, January 23, 1995.

## C.1 Algorithms

This section describes algorithms used for LPS processing.

## Algorithm #1: WRS Scene Identification

This is the top-level algorithm for identifying the center of a WRS scene (and by inference the remainder of the scene) within a Landsat 7 sub-interval. The problem it addresses is as follows. Given a sequence of {spacecraft time (t), attitude (A), ephemeris (X)} 3-tuples extracted from the sub-interval's PCD major frames (with all values corrected, time values computed from the PCD major frame time code, and all values converted to double precision real), and a WRS scene information look-up table (WRS\_LUT - described in detail below), identify the scene center of each full WRS scene contained within the sub-interval and output a record containing the scene information required for the sub-interval's metadata file.

Let WRS scene look-up table (WRS\_LUT) be a table with entries of the form:

(center\_lat/lon, corner\_lat/lons, path, row)

where

center\_lat/lon = nominal latitude and longitude of WRS scene center

corner\_lat/lons = nominal latitude and longitude at each WRS scene

path = the path number of this scene

row = the row number of this scene.

Discard the first N - 1{time, attitude, ephemeris} 3-tuples, where N = the minimum number of 3-tuples before encountering the scene center of a full scene within a sub-interval;

t<sub>prev</sub> <- the spacecraft time of the first 3-tuple in the reduced sequence;

P<sub>prev</sub> <- the latitiude/longitude of the first 3-tuple in the reduced sequence computed by Algorithm #2;

FOR each remaining {time, attitude, ephemeris} 3-tuple DO

t<sub>cur</sub> <- the spacecraft time of the 3-tuple;

P<sub>cur</sub> <- the latitude/longitude of this 3-tuple computed by Algorithm #2;

IF P<sub>prev</sub> < C £ P<sub>cur</sub> for a nominal scene center lat/lon (C) in WRS\_LUT THEN

t<sub>center</sub> <- time of datum nearest the nominal scene center by a TBD interpolation

method;

P<sub>center</sub> <- latitude/longitude of datum nearest the nominal scene center by a TBD interpolation method<sub>;</sub>

Horizontal display shift (HDS ) <- distance between <sup>P</sup>center and C by a TBD algorithm;

Major\_Frame\_Time <- the time code of the major frame containing the datum nearest the nominal scene center by a TBD method.

Center\_Scan <- the index (beginning at 1) of the major frame containing the datum nearest the nominal scene center.

Compute the Sun azimuth (AZ) and elevation (EL) at position <sup>P</sup>center and time<sup>t</sup>center using the algorithm described in <sup>Sun</sup> <sup>Azimuth</sup> <sup>and</sup> Elevation Algorithms, January 23, 1995;

Insert Major\_Frame\_Time, Center\_Scan, HDS, C , AZ, EL, WRS\_LUT[C].corner\_lat/lons, WRS\_LUT[C].path, and WRS\_LUT[C].row to the metadata for this scene.

END IF;

<sup>t</sup>prev <sup><-</sup> <sup>t</sup>cur <sup>;</sup>

$$
P _ { P r e v } < - P _ { c u r } ;
$$

END FOR

## Algorithm #2: Longitude and Latitude Algorithm

Latitude and Longitude Computation

The problem addressed by this algorithm is the following. Given spacecraft time (t), ephemeris ( X - Geocentric Inertial (GCI) spacecraft position vector), quaternion [(q1, q2,,q3, q4) - Euler parameters], Earth semimajor axis (a) and semiminor axis (b), transformation from ETM+ to spacecraft body matrix $( \left[ T _ { B M } \right] )$ , and ETM+ line of sight vector at the center of the mirror scan (V) , compute the geodetic latitude and longitude of the ground point in the ETM+'s view.

1. Compute the attitude matrix (transformation from GCI to body) from the Euler parameters (quaternion) obtained from PCD.

$$
\left[ \boldsymbol { Q } \right] = \left| \begin{array} { c c c c } { \boldsymbol { q } _ { 1 } ^ { 2 } - \boldsymbol { q } _ { 2 } ^ { 2 } - \boldsymbol { q } _ { 3 } ^ { 2 } + \boldsymbol { q } _ { 4 } ^ { 2 } } & { 2 ( \boldsymbol { q } \boldsymbol { q } _ { 2 } + \boldsymbol { q } _ { 3 } \boldsymbol { q } _ { 4 } ) } & { 2 \boldsymbol { q } _ { 1 } \boldsymbol { q } _ { 3 } - \boldsymbol { q } _ { 2 } \boldsymbol { q } _ { 4 } } \\ { 2 ( \boldsymbol { q } _ { 1 } \boldsymbol { q } _ { 2 } - \boldsymbol { q } _ { 3 } \boldsymbol { q } _ { 4 } ) } & { - \boldsymbol { q } _ { 1 } ^ { 2 } + \boldsymbol { q } _ { 2 } ^ { 2 } - \boldsymbol { q } _ { 3 } ^ { 2 } + \boldsymbol { q } _ { 4 } ^ { 2 } } & { 2 ( \boldsymbol { q } \boldsymbol { g } _ { 3 } + \boldsymbol { q } \boldsymbol { \ q } _ { 4 } ) } \\ { 2 ( \boldsymbol { q } _ { 1 } \boldsymbol { q } _ { 3 } + \boldsymbol { q } _ { 2 } \boldsymbol { q } _ { 4 } ) } & { 2 ( \boldsymbol { q } _ { 2 } \boldsymbol { q } _ { 3 } - \boldsymbol { q } _ { 1 } \boldsymbol { q } _ { 4 } ) } & { - \boldsymbol { q } _ { 1 } ^ { 2 } - \boldsymbol { q } _ { 2 } ^ { 2 } + \boldsymbol { q } _ { 3 } ^ { 2 } + \boldsymbol { q } _ { 4 } ^ { 2 } } \end{array} \right|
$$

2. Compute the transformation from spacecraft body to GCI (inverse of [Q])

$$
\left[ T _ { _ { I B } } \right] = \left[ Q \right] ^ { _ { 1 } }
$$

3. Compute the transformation from ETM+ to GCI

$$
[ T _ { _ { I M } } ] = [ T _ { _ { I B } } [ T _ { _ { B M } } ]
$$

4. Compute the cross-scan angle ( ) and along-scan angle ( ) of the ETM+ line of sight vector at the center of the mirror scan (V).

5. Solve the following vector equation to obtain the geocentric latitude ( ), right ascension ( ), and slant range ( d ) to the view point on the ground (see description of this in info provided by T. Keller for subroutine LPC).

$$
r \left[ \begin{array} { l } { \cos ( \varphi ) \cos ( \lambda ) } \\ { \cos ( \varphi ) \sin ( \lambda ) } \\ { \sin ( \varphi ) } \end{array} \right] = \vec { X } + d \big [ T _ { I M } \big ] \frac { - \mathsf { S i n } ( \sigma ) } { \mathsf { c o s } ( \sigma ) \mathsf { s i n } ( \theta ) } \left[ \begin{array} { l } { } { } \\ { } \\ { \mathsf { S i n } ( \varphi ) \mathsf { c o s } ( \mathsf { S } ) } \end{array} \right]
$$

where r is the radius from the center of the Earth to the view point.

6. Compute the Greenwich Hour Angle (GHA, right ascension of Greenwich) at the specified time using subroutine JGHAX.

7. Compute the longitude of the view point from right ascension and GHA.

$$
I o n { = } \lambda - G H A
$$

8. Compute the geodetic latitude from the geocentric latitude.

$$
\begin{array} { r } { I a t = \mathsf { a r c t a n } [ ( \pmb { \mathscr { a } } / b ) ^ { 2 } \tan ( \varphi ) ] } \end{array}
$$

where a and b are the Earth semimajor and semiminor axes (equatorial and polar radii), respectively.

## Algorithm #3: Sun azimuth and elevation algorithm

Algorithm Description

The problem to be addressed is this. Given the latitude (lat), longitude (lon), and spacecraft time (t)of the WRS scene center, compute the Sun azimuth (AZ) and elevation (EL) at the ground point. The algorithm is as follows.

1. Compute the Greenwich Hour Angle (GHA, right ascension of Greenwich) at time t using subroutine JGHAX.

2. Compute the GCI Sun vector $( \vec { R } _ { s u r } )$ at time t using subroutine SOL.

3. Define an Earth-fixed coordinate system centered at the latitude (lat)and longitude (lon) of interest with coordinate axes pointing north (N), east (E), and local vertical (V)

$$
\hat { V } = \left| \begin{array} { c } { { \cos ( I o n ) \cos ( I a t ) } } \\ { { \sin ( I o n ) \cos ( I a t ) } } \\ { { \sin ( I a t ) } } \end{array} \right| \qquad \hat { E } = \left| \begin{array} { c } { { - \sin ( I o n ) } } \\ { { \cos \angle I o n ) } } \\ { { 0 \ } } \end{array} \right| \qquad \hat { N } = \left| \begin{array} { c } { { - \cos ( I o n ) \sin ( I a t ) } } \\ { { - \sin ( I o n ) \sin ( I a t ) } } \\ { { \cos ( I a t ) } } \end{array} \right|
$$

4. Compute the transformation matrix from Earth-fixed to GCI

$$
\left[ G \right] = \left| \begin{array} { c c c } { \cos \left( G H A \right) } & { - \sin ( G H A ) } & { 0 } \\ { \sin ( G H A ) } & { \cos ( G H A ) } & { 0 } \\ { 0 } & { 0 } & { 1 } \end{array} \right|
$$

5. Transform the Earth-fixed coordinate axes to inertial

$$
\hat { V } _ { N } = \big [ G \big ] \hat { N }
$$

$$
\hat { V } _ { E } = \dot { G } | \hat { E }
$$

$$
\hat { V } _ { v } = \left[ G \right] \hat { V }
$$

6. Compute the azimuth and elevation (AZ, EL) of the Sun.

$$
A Z = \arctan \left( \frac { \hat { V } _ { N } \cdot \hat { R } _ { S u n } } { \hat { V } _ { E } \cdot \hat { R } _ { S u n } } \right)
$$

$$
E L = \arcsin \left( \hat { V } _ { \scriptscriptstyle V } \cdot \hat { R } _ { \scriptscriptstyle S u n } \right)
$$

## C.2 Computational Complexity

The complexity of algorithm depends primarily on the efficiency of the search for nominal scene center positions in WRS\_LUT. Although the algorithm describes a complete search at every iteration, the fact that, once a single scene center is identified, each successive scene center is also identified, allows the algorithm to reduce the search for a successive nominal scene centers after the first to a constant.

With this improvement the complexity is proportional to the number of {time, attitude, ephemeris} 3-tuples processed (i.e. O(N)). For each 3-tuple, the cost of the double precision floating point computations required will dominate. The algorithm requires a latitude and longitude computation for each candidate 3-tuple within the subinterval and two double precision tests (less-than, less-than-orequal-to). The latitude/longitude computation requires the computation of the GHA. For each identified scene center, the algorithm requires a Sun azimuth and elevation computation. This computation itself requires the computation of a GCI sun vector and GHA. On the assumption that the implementation will compute the GHA only once, Table 3 summarizes the floating point operations required for each algorithm component and lists both the total operations required for each 3-tuple and the additional operations required for each scene center. Details of the complexity analysis for Sun azimuth and elevation, GCI sun vector, and GHA computations can be found in the white paper, Sun Azimuth and Elevation Algorithms, January 32, 1995.

Table C-3 Floating Point Operations for WRS Scene ID Algorithms
<table><tr><td rowspan=1 colspan=1>Algorithm</td><td rowspan=1 colspan=1>+/ -</td><td rowspan=1 colspan=1>-N</td><td rowspan=1 colspan=1>*</td><td rowspan=1 colspan=1>÷</td><td rowspan=1 colspan=1>MOD</td><td rowspan=1 colspan=1>Round</td><td rowspan=1 colspan=1>Trig</td></tr><tr><td rowspan=1 colspan=1>Longitude/Latitude*</td><td rowspan=1 colspan=1>29</td><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>44</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>12</td></tr><tr><td rowspan=1 colspan=1>Azimuth/Elevation</td><td rowspan=1 colspan=1>24</td><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>36</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>18</td></tr><tr><td rowspan=1 colspan=1>GCI Sun Vector</td><td rowspan=1 colspan=1>7</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>7</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>5</td></tr><tr><td rowspan=1 colspan=1>GHA</td><td rowspan=1 colspan=1>579</td><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>560</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>45</td></tr><tr><td rowspan=1 colspan=1>Total for each3-tuple</td><td rowspan=1 colspan=1>608</td><td rowspan=1 colspan=1>8</td><td rowspan=1 colspan=1>604</td><td rowspan=1 colspan=1>6</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>67</td></tr><tr><td rowspan=1 colspan=1>Additional foreach scene center</td><td rowspan=1 colspan=1>31</td><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>43</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>23</td></tr></table>

Assuming 250 scenes per day, 24 seconds per scene, and 4 PCD major frames per second, 58,964,000 + 12,005,750 N (N = the average number of floating point operations for a trig function) floating point operations per day will be required.

## C.3 Estimated DSI

Table 4 presents DSI estimates for each of the algorithms. DSI for the top level scene identification algorithm are based on an assumed 5 DSI for each algorithm step plus a flat 100 DSI for initialization and maintenance of the WRS scene look-up table. DSI for the longitude/latitude computation is based on the number of floating point operations required (assuming 1 DSI per operation), the number of distinct intermediate values computed (assuming 1 DSI per value), a flat 100 DSI addition for matrix equation solution, a 30% overhead for initialization and termination handling, iteration, etc., and 100% overhead for exception handling. Details of the DSI estimates for Sun azimuth and elevation, GCI sun vector, and GHA computations appear in the white paper, Sun Azimuth and Elevation Algorithms, January 32, 1995.

Table C-4 DSI Estimates for WRS Scene Identification Algorithms

<table><tr><td rowspan=1 colspan=1>Algorithm</td><td rowspan=1 colspan=1>Estimated DSI</td></tr><tr><td rowspan=1 colspan=1>WRS Scene Identification Top-Leve</td><td rowspan=1 colspan=1>l180</td></tr><tr><td rowspan=1 colspan=1>Latitude/Longitude Computation</td><td rowspan=1 colspan=1>433</td></tr><tr><td rowspan=1 colspan=1>Sun Azimuth/Elevation at Spacecra</td><td rowspan=1 colspan=1>ft98</td></tr><tr><td rowspan=1 colspan=1>Sun Azimuth/Elevation at Earth</td><td rowspan=1 colspan=1>226</td></tr><tr><td rowspan=1 colspan=1>GCI Sun Vector</td><td rowspan=1 colspan=1>22</td></tr><tr><td rowspan=1 colspan=1>GHA</td><td rowspan=1 colspan=1>218</td></tr><tr><td rowspan=1 colspan=1>Total</td><td rowspan=1 colspan=1>1277</td></tr></table>

Appendix D - Acronym List
<table><tr><td></td><td>Appenux D- ACronyn List</td></tr><tr><td>ACCA</td><td>Automatic Cloud Cover Assessment</td></tr><tr><td>ADP</td><td>Attitude Data Points</td></tr><tr><td>Ao</td><td>Operational Availability</td></tr><tr><td>ANSI</td><td>American National Standards Institute</td></tr><tr><td>AOS</td><td>Advanced Orbiting Systems</td></tr><tr><td>API</td><td>Applications Programming Interface</td></tr><tr><td>BCH</td><td>Bose-Chaudhuri-Hocquenghem (error detection and correction scheme)</td></tr><tr><td>BER</td><td>Bit Error Rate</td></tr><tr><td>CADU</td><td></td></tr><tr><td>CASE</td><td>Channel Access Data Unit</td></tr><tr><td>CCA</td><td>Computer Aided Software Engineering Cloud Cover Assessment</td></tr><tr><td>CCB</td><td>Configuration Control Board</td></tr><tr><td>CIS</td><td>Centralized Information System</td></tr><tr><td>COTS</td><td>Commercial Off-the-Shelf</td></tr><tr><td>CPU</td><td>Central Processing Unit</td></tr><tr><td>CCSDS</td><td>Consultative Committee on Space Data System</td></tr><tr><td>CLCW</td><td>Command Link Control Word</td></tr><tr><td>CRC</td><td>Cyclic Redundancy Check</td></tr><tr><td>CRUD</td><td>Create, Retrieve, Update, Delete</td></tr><tr><td>CVCDU</td><td>Coded VCDU</td></tr><tr><td>DAMT</td><td>Distributed Application Monitor Tool</td></tr><tr><td>DAN</td><td>Data Availability Notice</td></tr><tr><td>DBMS</td><td>Database Management System</td></tr><tr><td>DD</td><td>Data Dictionary</td></tr><tr><td>DDE</td><td>Data Dictionary Entry</td></tr><tr><td>DDF</td><td>Data Distribution Facility</td></tr><tr><td>DDL</td><td>Data Definition Language</td></tr><tr><td>DFCB</td><td>Landsat &amp; System, Data Format Control Book</td></tr><tr><td>DFD</td><td>Data Flow Diagram</td></tr><tr><td>DPCP</td><td>Distributed Process Control Program</td></tr><tr><td>DSI</td><td>Delivered Source Instruction</td></tr><tr><td>DSN</td><td>Deep Space Network</td></tr><tr><td>DSP</td><td>Digital Signal Processing</td></tr><tr><td>DTA</td><td>Data Transfer Acknowledgment</td></tr><tr><td></td><td></td></tr><tr><td>ECS</td><td>EOSDIS Core System</td></tr><tr><td>EDC</td><td>EROS Data Center</td></tr><tr><td>EDAC</td><td>Error Detection and Correction</td></tr><tr><td>EDP</td><td>Ephemeris Data Points</td></tr><tr><td>EOL</td><td>End of Line</td></tr><tr><td>EOSDIS</td><td>Earth Observation Data Information System</td></tr><tr><td>ER</td><td>Entity Relationship</td></tr><tr><td>ERD</td><td>Entity Relationship Diagram</td></tr><tr><td>EROS</td><td>Earth Resources Óbservation System</td></tr><tr><td>ESMO</td><td>Earth Science Mission Operations</td></tr><tr><td>ETM+</td><td>Enhanced Thematic Mapper Plus (instrument)</td></tr><tr><td>EPA</td><td>Euler Parameters</td></tr><tr><td>FDDI</td><td>Fiber Distributed Data Interface</td></tr><tr><td>FHS ERR</td><td>First Half Scan Error</td></tr><tr><td>FTAM</td><td>File Transfer Access and Management</td></tr><tr><td>FTP</td><td>File Transfer Protocol</td></tr><tr><td>F&amp;PR</td><td>Functional and Performance Requirements</td></tr><tr><td>F&amp;PS</td><td>Functional and Performance Specification</td></tr><tr><td>GByte</td><td>Gigabyte</td></tr><tr><td>GCI</td><td>Geocentric Inertial</td></tr><tr><td>GHA</td><td>Greenwich Hour Angle</td></tr><tr><td>GOTS</td><td>Government Off-the-Shelf</td></tr><tr><td>GSFC</td><td>Goddard Space Flight Center</td></tr><tr><td>GTSIM</td><td>Generic Telemetry Simulator</td></tr><tr><td>GUI</td><td>Graphical User Interface</td></tr><tr><td>HDF</td><td>Hierarchical Data Format</td></tr><tr><td>HDS</td><td>Horizontal Display Shift</td></tr><tr><td>HWC</td><td>Hardware Component</td></tr><tr><td>HWCI</td><td>Hardware Configuration Item</td></tr><tr><td>IAS</td><td>Image Assessment System</td></tr><tr><td>ICD</td><td>Interface Control Document</td></tr><tr><td>ID</td><td>Identification</td></tr><tr><td>IDD</td><td>Interface Data Description</td></tr><tr><td>IDPS</td><td>Image Data Processing Subsystem</td></tr><tr><td>IM</td><td>Information Modeling</td></tr><tr><td>IMU</td><td>Inertial Measurement Unit</td></tr><tr><td>IPD</td><td>Information Processing Division</td></tr><tr><td>ISO</td><td>International Organization for Standardization</td></tr><tr><td>Kbps</td><td>Kilobits per Second</td></tr><tr><td>LAN</td><td>Local Area Network</td></tr><tr><td>LCC</td><td>life-cycle cost</td></tr><tr><td>LDTS</td><td>LPS Data Transfer Subsystem</td></tr><tr><td>LGS</td><td>Landsat 7 Ground Station</td></tr><tr><td>LPS</td><td>Landsat 7 Data Processing System</td></tr><tr><td>LP DAAC</td><td>Land Processes Distributed Active Archive Center</td></tr><tr><td>LRU</td><td>Line Replaceable Unit</td></tr><tr><td>LZP</td><td>Level Zero Processing</td></tr><tr><td>LOR</td><td>Level Zero Reformatted</td></tr><tr><td>MACS</td><td>Management and Control Subsystem megabits per second</td></tr><tr><td>Mbps</td><td>Major Frame Processing Subsystem</td></tr><tr><td>MFPS</td><td></td></tr><tr><td>MSCD</td><td>Mirror Scan Correction Data</td></tr><tr><td>MDT</td><td>Mean Downtime</td></tr><tr><td>MJF</td><td>Major Frame</td></tr><tr><td>MOC</td><td>Mission Operations Center</td></tr><tr><td>MO&amp;DSD</td><td>Mission Operations and Data Systems Directorate</td></tr><tr><td>MTBF</td><td>mean time between failures</td></tr><tr><td>MTTR MTTRes</td><td>mean time to repair</td></tr><tr><td></td><td>mean time to restore</td></tr><tr><td>NASA</td><td>National Aeronautics and Space Administration</td></tr><tr><td>NCC</td><td>Network Communication Center</td></tr><tr><td>NHB NCSA</td><td>NASA Handbook</td></tr><tr><td>NMAS</td><td>National Center for Supercomputing Applications</td></tr><tr><td>NMOS</td><td>Martin Marietta Astro Space</td></tr><tr><td>NOAA</td><td>Network Mission Operations Support</td></tr><tr><td></td><td>National Oceanic and Atmospheric Administration</td></tr><tr><td>PCD PCDS</td><td>Payload Correction Data</td></tr><tr><td>PN</td><td>PCD Processing Subsystem Pseudo-Random Processing</td></tr><tr><td>QA</td><td></td></tr><tr><td></td><td>Quality Assurance</td></tr><tr><td>RAID RAM</td><td>Redundant Array of Inexpensive Devices Random Access Memory</td></tr><tr><td>RDCS</td><td>Raw Data Capture Subsystem</td></tr><tr><td>RDPS</td><td>Raw Data Processing Subsystem</td></tr><tr><td>RMA</td><td>Reliability, Maintainability, and Availability</td></tr><tr><td>RMS</td><td></td></tr><tr><td>RS</td><td>Root, Mean, Square Reed-Solomon (error detection and correction</td></tr><tr><td></td><td>scheme)</td></tr><tr><td>RT</td><td>Real Time</td></tr><tr><td>SCCS SCLF</td><td>Source Code Control System</td></tr><tr><td>SCN DIR</td><td>Search, Check, Lock, Flywheel Scan Direction</td></tr><tr><td>SD</td><td>System Design</td></tr><tr><td>SDL</td><td></td></tr><tr><td>SDS</td><td>Storage Definition Language</td></tr><tr><td>SGI</td><td>System Design Specification</td></tr><tr><td>SHS ERR</td><td>Silicon Graphics, Incorporated</td></tr><tr><td></td><td>Second Half Scan Error</td></tr><tr><td>SLDPF</td><td>Spacelab Data Processing Facility</td></tr><tr><td>SMP</td><td>Systems Management Policy</td></tr><tr><td>SN</td><td>Space Network</td></tr><tr><td>SQL</td><td>Structured Query Language</td></tr></table>

<table><tr><td>SRR SRS SSDM STDN SV SVR4 SWCI</td><td>Software Requirements Review Software Requirements Specification SEAS System Development Methodology Spaceflight Tracking and Data Network Space Vehicle System V Release 4 Software Configuration Item</td></tr><tr><td>TBD TBR TMD UIL USGS</td><td>To Be Defined/Determined To Be Resolved Telemetry Decommutation User Interface Language</td></tr><tr><td>UTC</td><td>United States Geological Survey Universal Time Coordinated Versa Module European</td></tr><tr><td>VCDU VCDU-ID VCID VER VME</td><td>Virtual Channel Data Unit VCDU Identifier Virtual Channel ID Version Number</td></tr></table>