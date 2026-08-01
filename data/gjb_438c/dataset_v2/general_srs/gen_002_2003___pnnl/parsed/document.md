Pacific Northwest National Laboratory

Task Report for the Energy Efficient and Affordable Small Commercial and Residential Buildings Research Program

# Project 2.5 - Pattern-Recognition Based Fault Detection and Diagnostics

# Automated Diagnostics Software Requirements Specification Version 1.1

D.R. Sisk

M. R. Brambley

T. A. Carlon

R. S. Briggs

August 2003

Prepared for the U.S. Department of Energy under Contract DE-AC06-76RL01830

## DISCLAIMER

This report was prepared as an account of work sponsored by an agency of the United States Government. Neither the United States Government nor any agency thereof, nor Battelle Memorial Institute, nor any of their employees, makes any warranty, express or implied, or assumes any legal liability or responsibility for the accuracy, completeness, or usefulness of any information, apparatus, product, or process disclosed, or represents that its use would not infringe privately owned rights. Reference herein to any specific commercial product, process, or service by trade name, trademark, manufacturer, or otherwise does not necessarily constitute or imply its endorsement, recommendation, or favoring by the United States Government or any agency thereof, or Battelle Memorial Institute. The views and opinions of authors expressed herein do not necessarily state or reflect those of the United States Government or any agency thereof.

PACIFIC NORTHWEST NATIONAL LABORATORY operated by BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY under Contract DE-AC06-76RL01830

Printed in the United States of America

Available to DOE and DOE contractors from the   
Office of Scientific and Technical Information,   
P.O. Box 62, Oak Ridge, TN 37831-0062;   
ph: (865) 576-8401   
fax: (865) 576-5728   
email: reports@adonis.osti.gov

Available to the public from the National Technical Information Service, U.S. Department of Commerce, 5285 Port Royal Rd., Springfield, VA 22161 ph: (800) 553-6847 fax: (703) 605-6900 email: orders@ntis.fedworld.gov online ordering: http://www.ntis.gov/ordering.htm

# Final Report for the Energy Efficient and Affordable Small Commercial and Residential Buildings Research Program

# Project 2.5 – Pattern-Recognition based Fault Detection and Diagnostics

# Automated Diagnostics Software Requirements Specification Version 1.1

D. R. Sisk

M. R. Brambley

T. A. Carlon

R. S. Briggs

August 2003

Prepared for the U.S. Department of Energy under Contract DE-AC06-76RL01830

Pacific Northwest National Laboratory Richland, Washington 99352

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## Revision History

<table><tr><td rowspan=1 colspan=1>Date</td><td rowspan=1 colspan=1>Version</td><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=1>Author</td></tr><tr><td rowspan=1 colspan=1>7/31/2002</td><td rowspan=1 colspan=1>1.0</td><td rowspan=1 colspan=1>Initial version</td><td rowspan=1 colspan=1>DR Sisk, MR Brambley,TA Carlon, RS Briggs</td></tr><tr><td rowspan=1 colspan=1>8/30/2003</td><td rowspan=1 colspan=1>1.1</td><td rowspan=1 colspan=1>Revised version with Boiler Diagnostics</td><td rowspan=1 colspan=1>DR Sisk, MR Brambley,TA Carlon, RS Briggs</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr></table>

<table><tr><td colspan="1" rowspan="1">Automated Diagnostics</td><td colspan="1" rowspan="1">Version:      1.1</td></tr><tr><td colspan="1" rowspan="1">Software Requirements Specification</td><td colspan="1" rowspan="1">Date: 8/28/2003</td></tr><tr><td colspan="2" rowspan="1">Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## Table of Contents

1. Introduction   
1.1 Purpose 1   
1.2 Scope 1   
1.3 Definitions, Acronyms and Abbreviations 1   
1.4 References 3   
1.5 Overview 3   
2. Overall Description 4   
2.1 Product Perspective 4   
2.2 Product Functions 5   
2.3 User and Environment Characteristics 6   
2.4 General Constraints 6   
2.5 Use-Case Model Survey 7   
2.5.1 Introduction 7   
3. Requirements 8   
3.1 Use-Case Specifications 9   
3.1.1 Start and Stop Diagnostics Use Case 9   
3.1.2 Browse Current Diagnostics Use Case 11   
3.1.3 Browse Historical Diagnostics Use Case 12   
3.1.4 Configure Diagnostics Use Case 14   
3.1.5 Authenticate User 15   
3.2 Functionality 16   
3.2.1 General 16   
3.2.2 Preprocessing 16   
3.2.3 Diagnostic Process 19   
3.2.4 Output Processing 30   
3.3 Usability 30   
3.3.1 User Interface 30   
3.4 Supportability 31   
3.4.1 Error Reporting 31   
3.5 Interfaces 31   
3.5.1 User Interfaces 31   
3.6 Security 38   
3.7 Other Requirements 38   
4. Appendix A: Data Flow Diagrams of Diagnostic Processes for Chillers, Cooling Towers, and   
Chilled-Water Distribution 39   
5. Appendix B: Chiller, Cooling Tower, and Chilled-Water Distribution Data Dictionary 122   
6. Appendix C: Data Flow Diagrams for Boiler Diagnostic Processes 139   
7. Appendix D: Data Dictionary for Boilers 163

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

# Software Requirements Specification

## 1. Introduction

This document specifies requirements for a computerized automated diagnostic tool for the detection of faults in certain heating, ventilation, and air-conditioning (HVAC) system components. The automated diagnostic tool is being developed for Architectural Energy Corporation (AEC) by Battelle as part of a program sponsored by the California Energy Commission (CEC). Supplemental cost-share funds are provided by U.S. Department of Energy through the Pacific Northwest National Laboratory (PNNL).

## 1.1 Purpose

This Requirements Specification (RS) specifies the essential capabilities required of the automated diagnostic tool. The purpose of this document is to clarify for AEC, the California Energy Commission (CEC), the Office of Buildings Programs, Office of Energy Efficiency and Renewable Energy (EERN) of the U.S. Department of Energy, and the project team the results that must be achieved by the automated diagnostic tool. Any illustrative model presented in this document is used solely to explain the requirements and is NOT intended to address design or implementation issues.

This SRS also specifies key AEC, CEC, and EERN requirements for project deliverables, including documentation.

## 1.2 Scope

The automated diagnostic tool detects and identifies faults in chillers and cooling tower subsystems of HVAC units using sensed data acquired from the unit, unit specifications, unit installation and configuration data, and unit operation data (such as schedules). The tool is a software product that will be utilized primarily by building operators and facilities managers and only secondarily by HVAC service technicians, energy service providers, and operation supervisors. Building operators will use the tool to monitor units for which they are responsible, perhaps monitoring from a central control room within the building. Service technicians will utilize the product on site during repair and maintenance visits or off site between visits. Energy service providers, responsible for a number of customers and facilities, will use the product to monitor a number of units remotely, possibly in many different buildings, checking for inefficiencies and problems requiring dispatch of service personnel. Finally, building operator supervisors will use the tool to guide decisions on the assignment of operators and prioritization of work. The tool will provide the user with a visual indication of faults, descriptive information concerning the faults and their causes, and suggested corrective actions. The tool will store the results of diagnostics for subsequent retrieval and use.

The software require ments described in this document are applicable to HVAC systems and associated subsystems. Such subsystems can include chillers, cooling towers, and boilers. However, the initial version of the tool will focus on diagnostics for chillers and cooling towers only. The tool will automate diagnostic processes hitherto performed through a visual analysis of graphical data by a human expert.

The “Product Overview” section describes factors that affect the software and its requirements. The “Concept Example” appendix describes how the software would function in an example situation.

## 1.3 Definitions, Acronyms and Abbreviations

Some of the following definitions are taken or adapted from IEEE Std 610.12-1990 (IEEE 1993a) and IEEE Std 830-1984 (IEEE 1993b).

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

Authenticate — the process by which the tool establishes the identity and privileges of the user by obtaining an identifier and password from the user and checking it against a database of predefined users. The user becomes authenticated when the identifier and password match one of the predefined users in the tool’s database.

component — one of the parts that make up a software system. A component may be subdivided into other components [IEEE Std 610.12-1990]. Note: For the purpose of this specification, the term “component” will be used in preference to the term “module”

diagnostic result — the output of the diagnostic processing. This can either be an identified fault condition or the confirmation of the absence of a fault condition.

fixed data — data describing the characteristics of the unit under diagnosis, for example, specifications and design information, operating characteristics, set points, installation and configuration data, and operation data (such as schedules) that do not change on a regular basis.

functional requirement — a requirement that specifies a function that a software system or software component must be able to perform [IEEE Std 610.12-1990]. In this requirements specification, functional requirements specify how the inputs to the software product should be transformed into outputs [IEEE Std 830-1984].

interface requirement — a requirement that specifies an external item with which a software system or software component must interact, or that sets forth constraints on formats, timing, or other factors caused by such an interaction [IEEE Std 610.12-1990]

module — see component

product — (for this document) a software system or software component-along with any necessary data and documentation-for which requirements are specified in a requirements specification

requirement — (1) a condition or capability needed by a customer to solve a problem or achieve an objective; (2) a condition or capability that must be met or possessed by a software system or software component to satisfy a contract, standard, specification, or other formally imposed document; (3) a documented representation of a condition or capability as in (1) or (2) [adapted from IEEE Std 610.12- 1990]

requirements specification (RS) — a document of the essential requirements (functions, design constraints, and attributes) of the software and/or hardware and their external interfaces [adapted from IEEE Std 610.12-1990]

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

Sensed data — data that are measured through electronic or mechanical detection. Typically this data varies at such a rate, e.g., in real time, hourly, daily, weekly, or is otherwise difficult to estimate or model such that an accurate characterization of it can only be gained through such detection. This data includes temperatures, pressures, electrical current, machine state, etc.

software system — a collection of software components related in such a way as to produce a result greater than what their parts, separately, could produce

subsystem — a discrete part of an HVAC system, e.g., chiller or cooling tower.

unit — a complete HVAC system

usability — the ease with which a user can learn to operate, prepare inputs for, and interpret outputs of a software system or software component [IEEE Std 610.12-1990].

## 1.4 References

The following are references supporting these specifications:

## 1.5 Overview

Product Overview-- This section provides a descriptive overview of the automated diagnostic tool, its users and operating environment, and general factors that affect requirements. It lays the foundation for understanding the specific requirements that follow.

Specific requirements are specified in the following categories:
<table><tr><td rowspan=1 colspan=1>Category</td><td rowspan=1 colspan=1>Descriptions</td></tr><tr><td rowspan=1 colspan=1>OverallDescription</td><td rowspan=1 colspan=1>An overview of the expected product use andcontext including user characteristics, constraints,and assumptions.</td></tr><tr><td rowspan=1 colspan=1>FunctionalRequirements</td><td rowspan=1 colspan=1>describes the core capability and operatingcharacteristics required of the diagnostic tool bythe client.</td></tr><tr><td rowspan=1 colspan=1>ExternalInterfaceRequirements</td><td rowspan=1 colspan=1>includes general user interface requirements andlogical characteristics of interfaces between theautomated diagnostic tool, data acquisitionsystem, and data storage system. Specific userinterface requirements are being developedindependently as part of the Phase A Prototype.</td></tr><tr><td rowspan=1 colspan=1>SecurityRequirements</td><td rowspan=1 colspan=1>specifies requirements for safeguarding customerdata</td></tr><tr><td rowspan=1 colspan=1>OtherRequirements</td><td rowspan=1 colspan=1>includes special operations required by end users,and documentation requirements specified by theclient.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

Appendix A: Data Flow Diagrams of Diagnostic Processes for Chillers, Cooling Towers and Chilled Water Distribution provides diagrams showing the data flows and data-processing that lead from fixed data and sensed data to diagnostic conclusions.

Appendix B: Data Dictionary for Chillers, Cooling Towers and Chilled Water Distribution provides a tabular listing of known system data corresponding to their use in Appendix A.

Appendix C: Data Flow Diagrams for Basic Boiler Diagnostics provides diagrams and mini-specs showing data flows and data processing that lead from fixed data and sensed data to diagnostic conclusions.

Appendix D; Data Dictionary for Boilers provides a tabular listing of all known system data elements corresponding to their use in Appendix C.

## 2. Overall Description

The following overview of the automated diagnostic tool supplies context for the specific requirements presented in later sections. The purpose of this information is to make the specific requirements easier to understand. All specific requirements are numbered in later sections.

## 2.1 Product Perspective

Currently, diagnostics on HVAC units and subsystems are performed largely on a manual basis. Sensed data, e.g., temperatures and pressures, are obtained from one or more data acquisition devices. These devices measure and store sensed data over periods of several days to several weeks. Prior to the diagnostic process, data from these devices is input to graphical display software for visual inspection by a human expert. The expert, relying on technical expertise and results of previous diagnostic experience, evaluates the condition of the unit and subsystems based on visual plots of the data. This process is depicted in Figure 1.

![](images/ca2aa1e638b208615e43ca5299c37fb8bdbf09420cb73bdf26ea3987d891ab7a.jpg)  
Figure 1. Current HVAC Diagnostic Process

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

The process depicted in Figure 1 can be partitioned into three logical components. These components are delineated in the diagram by dashed lines and are the data-preprocessing component, the diagnostic component, and output component. The diagnostic tool described in this document will replace the current process with an automated one based on algorithms derived from expert practices. These algorithms operate without the need for data visualization or human expert input. Diagnostic results will be displayed to the user and stored for subsequent retrieval and analysis. For the purposes of this document, the automated diagnostic tool will be assumed to preserve the logical construction of the current process. This construction is depicted in Figure 2.

![](images/55f5cacd61f0475f7ff0285839856cbdf2c7e7ce7b61532703e114ff8969218a.jpg)  
Figure 2. Logical Construction of HVAC Diagnostic Process

## 2.2 Product Functions

As previously stated, the functionality of the automated diagnostic tool can be partitioned into three logica components: the data preprocessing component, the diagnostic component, and the output component.

The data-preprocessing component obtains data describing the subsystem under diagnosis and reduces, filters, and otherwise prepares the data for input to the diagnostic component. This data includes sensed data, e.g., temperatures, pressures, electrical current, machine state, etc., as well as fixed data describing the characteristics of the subsystem under diagnosis, for example, specifications and design information, operating characteristics and set points, etc. The data may be processed through averaging, trending, or other statistical analysis. Sensed data can originate from data acquisition hardware either in real time or at some arbitrary time after acquisition. Fixed data will generally be compiled prior to operation of the diagnostic tool and be obtained from permanent storage when needed. Specific requirements will be placed on the data-preprocessing component only with respect to types of data to be input and the format and interface requirements of this input. However, the component is described here to provide insight into the operation of the software.

The diagnostic component will detect and identify faults in the operation of HVAC subsystems based on sensed and fixed data input from the data-preprocessing component. The diagnostic algorithms used for fault detection will be derived from current expert practices by AEC. The faults identified by the

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

diagnostic will be enumerated and described under the functional requirements section.

The output component will display and record results output from the diagnostic component. The results of the diagnostics will be displayed to the user in a simple, graphical and textual format. The results will also be stored to permanent storage for subsequent retrieval and analysis.

## 2.3 User and Environment Characteristics

As previously stated, users of the automated diagnostic tool will include service technicians, energy service providers, building operators, and building operator supervisors. Installed platforms could include portable computers, handheld devices, and personal workstations in control rooms and offices. Installed platforms may communicate with the HVAC unit under diagnosis using wireless interfaces, direct point-to-point connections, or over Internet or local area network. Platform operating systems will be initially restricted to Microsoft Windows-compatible systems.

The computer expertise of the user base could vary over a wide range. Some users could be quite sophisticated, others familiar with only the most rudimentary computer-based tasks. However, it is expected that all users will have a good fundamental understanding of HVAC units. Setting up and operating the automated diagnostic tool should require minimal user input.

Service technicians are expected to use the software as often as their service tasks dictate, perhaps several times a day for periods up to about one hour, in close proximity to the HVAC unit and possibly out of doors. They may also set up the diagnostic tool to collect data continuously offsite at their offices and inspect the data periodically to identify faults or confirm proper operation. Building operators are expected to use the software on an occasional basis every day. The tool would collect data and process it continuously but the operators would only check the results periodically. They may view results for only a few seconds to check the status of equipment while passing through a control room or may sit at a monitor for several minutes more carefully inspecting the diagnostic results and other information available on the tool’s display. Energy service providers and building operator supervisors could potentially use the software in a more continuous mode, allowing it to operate undisturbed for many hours or days to record diagnostic results over a period of time.

See the “Concept Example” appendix for a detailed example of how the automated diagnostic tool will be used.

## 2.4 General Constraints

The automated diagnostic tool must support a wide variety of users with respect to computer expertise. In addition, different users will have different expectations for the tool with respect to data presentation and functionality. For instance, some users will simply require an immediate diagnostic result while other users may be interested in diagnostic results generated over an arbitrary time that can be subsequently reviewed.

The tool must provide a capability to manually input and edit “fixed” data, i.e., data that does not vary in real-time. Such data includes HVAC unit set points, specifications, and configuration information. This data must be stored for subsequent use by the diagnostic tool for review and verification by other users and management. The tool should provide for configuration management of fixed data.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

The user must have the capability to configure the tool for continuous diagnostic analysis over an indefinite period of time. In this mode, the tool will record diagnostic results for subsequent review. No printed reports will be required of the tool, but the tool must print screen images of diagnostic results and historical data at user request and must provide long term storage of diagnostic results and permit the user to supply metadata relevant to the results, e.g., location, HVAC serial number, model number, user name, date, etc.

The tool will not provide capability for additional user-defined analysis of the diagnostic results, results will be provided in a simple, final, definitive manner. However, the tool may provide the user the capability to adjust the sensitivity of the diagnostic algorithms to increase the probability of exposing typically undetected diagnostic events or concealing detected diagnostic events (including false detections).

The tool will be capable of obtaining sensed data from a variety of sources. Such sources should include real-time data acquisition devices and data files containing previously acquired data.

The current version of the tool will include diagnostic algorithms for cooling tower and chiller subsystems of HVAC units. However, the design of the software should support the incorporation of diagnostic algorithms for additional HVAC subsystems. In addition, the tool should support modification or replacement of existing diagnostic algorithms.

The automated diagnostic tool will be restricted to Microsoft Windows-compatible operating systems.

## 2.5 Use-Case Model Survey

This section provides an overview of the use case model that describes the operation of the user interface. Actual use cases that specifically define the operation of the user interface are presented in the requirements section.

## 2.5.1 Introduction

The use case model consists of five use cases as depicted in Figure 3. The main actor in the use case model is the human user. This actor is generalized as “User”. The User can be further specified as a general user or administrator. The general user has no ability to modify system settings. The admin istrator user is able to modify certain settings. The use case “Start and Stop Diagnostics” describes the process by which the administrator user activates and ceases diagnostic processing. The use case “Browse Current Diagnostics” describes the process by which the user views current diagnostic results. The use case “Browse Historical Diagnostics” describes the process by which the user views historical diagnostic results. The use case “Configure Diagnostics” describes the process by which the administrator user adjusts diagnostic parameters used in the diagnostic process. The use case “Authenticate User” describes the process by which the user makes known to the tool the privileges to which they are entitled.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

![](images/c1941973c4a3dfdb9dae392dc205dcdd82d7baefd3bd416ba5869f095903e10f.jpg)  
Figure 3. Use Case Model

## 3. Requirements

The requirements in this document are organized according to the categories listed in Table 1.

Table 1. Categories of Software Requirements
<table><tr><td colspan="1" rowspan="1">Requirement Category</td><td colspan="1" rowspan="1">General Description and Purpose</td></tr><tr><td colspan="1" rowspan="1">Use-Case Specifications</td><td colspan="1" rowspan="1">specify, in terms of use cases, the expected interactions and behavior of the softwarewith respect to the defined actors.</td></tr><tr><td colspan="1" rowspan="1">Functionality</td><td colspan="1" rowspan="1">specify functions that a system or component must be able to perform — thefundamental software actions that transform inputs into outputs</td></tr><tr><td colspan="1" rowspan="1">Automated Diagnostics</td><td colspan="1" rowspan="1">Version:      1.1</td></tr><tr><td colspan="1" rowspan="1">Software Requirements Specification</td><td colspan="1" rowspan="1">Date: 8/28/2003</td></tr><tr><td colspan="2" rowspan="1">Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Usability</td><td rowspan=1 colspan=1>specify factors affecting how easily users can learn to operate a system orcomponent, prepare its inputs, and interpret its outputs</td></tr><tr><td rowspan=1 colspan=1>Supportability</td><td rowspan=1 colspan=1>include requirements affecting how easily a system or component can be maintainedto meet its original requirements or extended to meet modified requirements</td></tr><tr><td rowspan=1 colspan=1>Interfaces</td><td rowspan=1 colspan=1>specify requirements for user, hardware, software, and communication interfaces, asapplicable.</td></tr><tr><td rowspan=1 colspan=1>Security</td><td rowspan=1 colspan=1>specify needs for protecting the software from accidental or malicious access, use,modification, destruction, or disclosure</td></tr><tr><td rowspan=1 colspan=1>Other Requirements</td><td rowspan=1 colspan=1>include special requirements that do not fit into previous categories</td></tr></table>

## 3.1 Use-Case Specifications

This section describes the fi ve main use cases describing the functionality of the user interface. These use cases are “Start and Stop Diagnostics”, “Browse Current Diagnostics”, “Browse Historical Diagnostics”, “Configure Diagnostics”, and “Authenticate User”. The use cases “Start and Stop Diagnostics” and “Configure Diagnostics” include the use case “Authenticate User”.

## 3.1.1 Start and Stop Diagnostics Use Case

## 3.1.1.1 Brief Description

This use case provides the actor the means to start and stop diagnostic processing. The actor in this case is the administrator user (see 2.5.1).

## 3.1.1.2 Flow of Events

The use case begins just prior to when the user launches the application.

## 3.1.1.2.1 Basic Flow – Start Diagnostics

1. The user launches the tool by double-clicking the icon associated with the tool or typing the application’s name.

2. The tool momentarily displays a splash screen identifying the tool, identifying developing and sponsoring organizations as appropriate, and listing copyright information.

3. The tool displays the main window of the tool.

4. The user starts the diagnostic processing by selecting a menu item named “Start Diagnostics” from a drop down menu named “Status”.

5. Include (Authenticate User). If the user has the appropriate privilege (i.e., the user is the administrator user) the tool requests a confirmatory response from the user to start the diagnostic processing.

6. If the user confirms the desire to start diagnostic processing, the tool starts the processing and displays an animated indication that diagnostic processing is active.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

7. If the user responds negatively to the confirmation, the tool does not start the diagnostic processing but the user remains authenticated.

8. If the user does not have the appropriate privilege, the tool does not start the diagnostic processing.

9. The user secures the tool by selecting a menu item named “Logout” from the drop down menu named “File”.

10. The tool returns the current user’s privileges to those of the general user.

11. If a period of 15 minutes elapses whereby the user does not secure the tool, the users privileges will automatically revert to those of a general user.

## 3.1.1.2.2 Alternative Flow

## 3.1.1.2.2.1 Stopping Diagnostic Processing

1. The user can stop diagnostic processing at any time after the diagnostic processing has started by selecting the “Stop Diagnostics” menu item from the main menu entitled “Status”.

2. If the user is not authenticated as the administrator user, include (Authenticate User) to validate privileges for stopping diagnostic processing.

3. If the user has the appropriate privilege, the tool requests confirmation to stop diagnostic processing.

4. If the user responds positively to the confirmation, the tool stops diagnostic processing and indicates the stopped condition. Otherwise the software performs no function but the user remains authenticated.

5. If the user selects the “Exit” menu item from the main menu entitled “File” and the diagnostic processing is not active, the tool exits.

6. If the user selects “Exit” and the diagnostic processing is active, include (Authenticate User), if the user is not already validated, to verify the user’s privilege to stop diagnostic processing.

7. If the user is permitted to stop diagnostic processing, the tool stops the processing and exits. Otherwise, the software performs no function.

## 3.1.1.3 Special Requirements

There are no special requirements for this use case.

## 3.1.1.4 Preconditions

There are no preconditions for this use case.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.1.1.5 Postconditions

There are no postconditions for this use case.

## 3.1.1.6 Extension Points

There are no extension points for this use case.

## 3.1.2 Browse Current Diagnostics Use Case

## 3.1.2.1 Brief Description

This use case provides the actor the means to view current diagnostic results. The actor in this case is the user (see 2.5.1).

## 3.1.2.2 Flow of Events

The use case begins with the tool executing and displaying a list of buildings under diagnosis on the main (initial) window.

## 3.1.2.2.1 Basic Flow – Browse Current Diagnostics

1. The tool displays the main (initial) window, listing buildings under diagnosis.

2. The user selects a building of interest.

3. The tool displays the subsystems window, tiled on top the main (initial) window.

4. The user selects a subsystem of interest.

5. The tool displays the condition window, tiled on top the subsystems window.

6. The user selects a diagnostic of interest.

7. The tool displays the diagnostic information window for that diagnostic.

## 3.1.2.2.2 Alternative Flow

1. At any window except the initial window, the user may click the “Back” button to dismiss the current window and re-establish the previous window as the current window. The user may then make a new selection.

2. The user may click a button labeled “Print” on the diagnostic information window to print an image of the window.

3. The tool displays a window listing possible items to print including the diagnostic information window.

4. The user selects the diagnostic information window and clicks the “OK” button to print the window.

## 3.1.2.3 Special Requirements

There are no special requirements for this use case.

## 3.1.2.4 Preconditions

There are no preconditions for this use case.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.1.2.5 Postconditions

The diagnostic processing will not cease or be negatively impacted during the activities of this use case.

## 3.1.2.6 Extension Points

There are no extension points for this use case.

## 3.1.3 Browse Historical Diagnostics Use Case

## 3.1.3.1 Brief Description

This use case provides the actor the means to view historical diagnostic results. The actor in this case is the user (see 2.5.1).

## 3.1.3.2 Flow of Events

The use case begins with the tool displaying the diagnostic information window, itself displaying a description of a diagnostic of interest.

## 3.1.3.2.3 Basic Flow – Browse Historical Diagnostics

1. The user clicks the “History” button.

2. The tool displays the diagnostic history window depicting the historical results of the selected condition of interest over the default viewing period in the form of a color map. The window provides a scroll bar for scrolling through historical results if data are available prior to the default viewing period. The default viewing period extends backward one week prior to the current date. Sliding the scroll bar does not change the viewing period displayed. The default time resolution for the window is one hour.

3. The user slides the scroll bar backward or forward to view previous results up to the current time.

4. The tool displays the results within a viewing period of one week, adding results to the beginning or ending of the period while dropping results of the opposite end. The tool does not change the viewing period.

5. The user may close the diagnostic history window by clicking the “Close” button.

6. The tool dismisses the diagnostic history window and the diagnostic information window and makes the condition window the current window.

## 3.1.3.2.4 Alternative Flows

## 3.1.3.2.4.1 Changing the Viewing Period

1. The user selects a new viewing period from a list of periods provided by the tool.

2. The tool redisplays the historically data over the new viewing period.

## 3.1.3.2.4.2 Zooming

1. The user selects a period of time within the displayed viewing period over which to expand or contract in time.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

2. The tool expands or contracts the selected period. If expanding, the selected period becomes the new viewing period. If contracting, the new viewing period becomes twice as long as the selected period and encloses it.

## 3.1.3.2.4.3 Displaying Historical Diagnostic Information

1. The user double-clicks a cell in the history window.

2. The tool dismisses the current diagnostic information window if displayed. After a noticeable delay of approximately one second, the tool displays the diagnostic information window associated with the cell selected.

## 3.1.3.2.4.4 Browsing Arbitrary History Intervals

1. The user specifies a start time and end time for an historical interval of interest using calendar controls.

2. The tool displays historical results beginning with the first result on or after the specified start time up to the end time. The view is confined to the previously selected viewing period.

## 3.1.3.2.4.5 General Alternative Flows

1. At the diagnostic information window, the user may click the “Close” button to dismiss the window and make the condition window the current window if the diagnostic history window is not displayed.

2. If the user attempts to close the diagnostic information window and the diagnostic history window is still displayed, the diagnostic information window is dismissed but the diagnostic history window remains.

3. If the condition window is closed, then both the diagnostic information and diagnostic history windows are closed if open.

4. If the user does not specify an end time for the history interval in 3.1.3.2.4.1 Browsing Arbitrary History Intervals (1), it defaults to the current time.

## 3.1.3.3 Special Requirements

There are no special requirements for this use case.

## 3.1.3.4 Preconditions

The diagnostic processing need not be active for this use case. A diagnostic information window must be displayed for this use case to begin.

## 3.1.3.5 Postconditions

The diagnostic processing will not cease or be negatively impacted during the activities of this use case.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.1.3.6 Extension Points

There are no extension points for this use case.

## 3.1.4 Configure Diagnostics Use Case

## 3.1.4.1 Brief Description

This use case provides the actor the means to configure the diagnostic tool. This includes defining the buildings containing systems to be diagnosed, defining the systems themselves, specifying equipment setpoints, selecting diagnostic sensitivity, and modifying fixed data. The actor in this case is the administrator user (see 2.5.1).

## 3.1.4.2 Flow of Events

The diagnostic tool is executing prior to the processing of this use case and only the main window of the tool is displayed.

## 3.1.4.2.5 Basic Flow – Configure Diagnostics

1. When presented with the main window, the user may select the “Configure Diagnostics” menu item from the menu entitled “File”.

2. If the user has not already been authenticated as the administrator user, include (Authenticate User).

3. If the user has the appropriate privilege, the tool displays the configuration window.

4. The user may click the “Recall” button to read previously saved changes from a disk file or database.

5. The tool populates the window with the data from the disk file.

6. The user makes the desired changes to the configuration and can click the button labeled “Save” to save the changes. Otherwise, the user can click the button labeled “Close”.

7. If the user clicks the button labeled “Save”, the tool will request confirmation to save the changes.

8. If the user confirms, the tool will request a name for the disk file in which to save the modified data to permanent storage.

9. The user will enter a name for the file or cancel the operation.

10. If the user enters a name for the file, the tool will save the changes. If the user cancels the operation, the tool will perform no function.

11. If the tool completes the save operation, the tool will ask the user if the changes are to be relayed to the diagnostic processing for immediate use.

12. If the user confirms the changes are to be relayed to the diagnostic processing, the tool relays the changes if the processing is currently active. Otherwise, the tool does not relay the changes.

13. If the user clicks the button labeled “Close”, the tool will request confirmation for the close and the potential loss of any changes.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

14. If the user confirms, the tool will dismiss the configuration window, ignoring any changes and returns the user to the main window. If the user rejects the initia desire to close, the tool will perform no function.

## 3.1.4.2.6 Alternative Flows

There are no alternative flows for this use case.

## 3.1.4.3 Special Requirements

There are not special requirements for this use case.

## 3.1.4.4 Preconditions

The main window of the tool must be the only window active for the tool prior to execution of this use case.

## 3.1.4.5 Postconditions

Any changes made by the administrator user to the diagnostic tool will take affect immediately if requested by the user.

## 3.1.4.6 Extension Points

There are no extension points for this use case.

## 3.1.5 Authenticate User

## 3.1.5.1 Brief Description

This use case establishes the privileges of the user for certain functions of the tool.

## 3.1.5.2 Flow of Events

This use case begins when another use case requires its instantiation.

## 3.1.5.2.7 Basic Flow

1. The tool displays a window for entry of authenticating information, i.e., user name and password, to validate and establish the privileges of the user.

2. The user enters their user name and password.

3. The tool attempts to authenticate the user and indicates whether authentication has succeeded or not.

4. If authentication is unsuccessful, the user is returned to the authentication window to reenter the information.

5. The tool permits three attempts at authentication before dismissing the authentication window and returning the user to the previous window.

6. The user may cancel the authentication process at any time and return to the previous window.

## 3.1.5.2.8 Alternative Flows

There are no alternative flows for this use case.

## 3.1.5.2.9 Special Requirements

There are no special requirements for this use case.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.1.5.2.10 Preconditions

There are no preconditions for this use case.

## 3.1.5.2.11 Postconditions

There are no postconditions for this use case.

## 3.1.5.2.12 Extension Points

There are no extension points for this use case.

## 3.2 Functionality

This section describes the functional requirements of the software, that is, requirements describing the core functions the software must perform. This section begins with general requirements relevant to the tool as a whole. Subsequently, requirements are organized by the logical construction of the tool as data processing progresses from preprocessing to output processing.

## 3.2.1 General

The following general requirements pertain equally to the logical partitions of the tool.

3.2.1.1 Users of the tool shall be classified into two types. The first type, general user, shall only be permitted to utilize a limited set of the capabilities of the tool. These capabilities are listed in Table $2 _ { \triangleq }$ Typically a general user is only permitted to view the results of diagnostic processing either current or historical. The second type, administrator, shall be permitted all the privileges of the general user plus those identified in Table 2. The administrator is permitted all the privileges of the general user in addition to the privileges to configure the system and modify fixed data and diagnostic settings.

Table 2 User Privileges
<table><tr><td rowspan=1 colspan=1>General UserPrivileges</td><td rowspan=1 colspan=1>Administrator PrivilegesBeyond General User&#x27;s</td></tr><tr><td rowspan=1 colspan=1>Browse CurrentDiagnostics</td><td rowspan=1 colspan=1>Start/Stop Diagnostics</td></tr><tr><td rowspan=2 colspan=1>Browse HistoricalDiagnostics</td><td rowspan=1 colspan=1>Configure Diagnostics</td></tr><tr><td rowspan=1 colspan=1>Define sensed data inputunits</td></tr></table>

## 3.2.2 Preprocessing

The automated diagnostic tool shall input sensed data in real time from data acquisition devices and the HVAC unit under diagnosis as well as from data files containing previously acquired data, though not simultaneously. In addition, the tool shall input fixed data provided by the user. Sensed and fixed data used by the tool in performing automated diagnostics shall be stored to permanent storage for post-analysis by the diagnostic process and viewing of the results.

3.2.2.1 The tool shall input sensed data in real time from data acquisition devices and the HVAC unit under diagnosis. The absolute time of input will be associated with each sensed data item for its complete lifecycle, including permanent storage. The time will be determined at the instant the acquisition of the sensed data is complete.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

3.2.2.2 The tool shall permit sensed data to be input from an electronic file, though not simultaneously with sensed data from external acquisition hardware. When inputting sensed data from an electronic file, only one file shall be used containing all necessary sensed data. The file shall be an ASCII text file containing only columns delimited by a single tab character or single comma. The file shall begin with a required header. The first column of the header will list, at a minimum, the entries “”Building Identifier” and “Input Identifier” in that order. Following columns on the Input Identifier row will list integer input identifiers. Following columns on the Building Identifier row will list corresponding integer building identifiers for the inputs. One or more comment rows may exist above and below these required rows. These comment rows are identified by a ‘#’ as the first character of the first column. These rows are ignored by the tool. The first uncommented column in the file after the required headers shall list the absolute time, in ascending order, associated with all entries in subsequent columns of the row. Each additional column in the file shall pertain to one and only one sensed parameter. Data values in the same row of the file correspond to identical time values. All columns in the file shall have the same number of rows. An example input file is presented in Table 3. When the tool is processing sensed data from an input file, the tool is considered to be operating in “batch mode”.

Table 3 Example Input Data File Reflecting Specified Format
<table><tr><td rowspan=1 colspan=1>#Test Run</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>#Sensor Name</td><td rowspan=1 colspan=1>Temperature</td><td rowspan=1 colspan=1>Flow</td><td rowspan=1 colspan=1>Pressure</td></tr><tr><td rowspan=1 colspan=1>Building Identifier</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=1>Input Identifier</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>3</td></tr><tr><td rowspan=1 colspan=1>12/14/018:43</td><td rowspan=1 colspan=1>12.4</td><td rowspan=1 colspan=1>35.8</td><td rowspan=1 colspan=1>407.3</td></tr><tr><td rowspan=1 colspan=1>12/14/0113:30</td><td rowspan=1 colspan=1>5.4</td><td rowspan=1 colspan=1>955.1</td><td rowspan=1 colspan=1>971.0</td></tr><tr><td rowspan=1 colspan=1>12/14/01 20:01</td><td rowspan=1 colspan=1>123.5</td><td rowspan=1 colspan=1>576.21</td><td rowspan=1 colspan=1>491.4</td></tr></table>

3.2.2.3 Each sensed data item will be qualified as to its certitude during the acquisition process. Sensed data will be considered in doubt if acquisition of the data was not possible (for example, if an error occurs during communication with the acquisition hardware), or the data is outside the range of possible values. Otherwise, the sensor value will be deemed accurately acquired.

3.2.2.4 The software will deem sensed data in doubt if acquisition of the data is not possible, due to communication failures, for a default number of successive samples. The default is dependent on sensor type. These default values are specified in Table 4. The number of successive samples for a given sensor type shall be modifiable by the administrator. Data not successfully acquired will be deemed “missing data”.

Table 4 Default Number of Failed Successive Samples Indicating Sensor Data Acquisition Problem.

<table><tr><td rowspan=1 colspan=1>Sensor Type</td><td rowspan=1 colspan=1>Default Number ofFailed SuccessiveSamples</td></tr><tr><td rowspan=1 colspan=1>Temperature</td><td rowspan=1 colspan=1>3</td></tr><tr><td rowspan=1 colspan=1>Current</td><td rowspan=1 colspan=1>3</td></tr><tr><td rowspan=1 colspan=1>Switch</td><td rowspan=1 colspan=1>3</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

3.2.2.5 Sensed data used in or supporting diagnostic analyses shall be saved to permanent storage.

3.2.2.6 The occurrence of missing data shall be indicated in permanent storage by a unique and obvious place holder or indicator, e.g., a null value or sequence of characters that cannot be confused with nonmissing data.

3.2.2.7 Sensed data input to the tool shall be stored to permanent storage with a precision of three significant figures.

3.2.2.8 Sensed data input to the tool shall be validated with respect to its expected range of values.   
Sensed data shall be assigned the ranges listed in Table 5 by default.

Table 5 Default sensed data expected ranges
<table><tr><td rowspan=1 colspan=3>Sensor                       Expected Minimum       Expected MaximumValue                        Value</td></tr><tr><td rowspan=1 colspan=1>Ambient Temperature</td><td rowspan=1 colspan=1>-40 F</td><td rowspan=1 colspan=1>130 F</td></tr><tr><td rowspan=1 colspan=1>Ambient wet-bulb Temperature</td><td rowspan=1 colspan=1>-40 F</td><td rowspan=1 colspan=1>100F</td></tr><tr><td rowspan=1 colspan=1>Chilled Water Supply Temperature</td><td rowspan=1 colspan=1>30F</td><td rowspan=1 colspan=1>80F</td></tr><tr><td rowspan=1 colspan=1>CT Sump Temperature</td><td rowspan=1 colspan=1>32F</td><td rowspan=1 colspan=1>130F</td></tr><tr><td rowspan=1 colspan=1>CT Inlet Temperature</td><td rowspan=1 colspan=1>35F</td><td rowspan=1 colspan=1>130F</td></tr><tr><td rowspan=1 colspan=1>Compressor Current (or Power)</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>NA, Chiller dependent</td></tr><tr><td rowspan=1 colspan=1>Condenser Pump Current (or Power)</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>200 amps</td></tr><tr><td rowspan=1 colspan=1>Chilled Water Pump Current (orPower)</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>200 amps</td></tr><tr><td rowspan=1 colspan=1>Secondary Chilled Water Pump(s)Current (or Power)</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>200 amps</td></tr><tr><td rowspan=1 colspan=1>Cooling Tower Fan(s) Current (orPower)</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>200 amps</td></tr><tr><td rowspan=1 colspan=1>Condenser Fan(s) Current (or Power)</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>200 amps</td></tr><tr><td rowspan=1 colspan=1>Supply Fan(s) Current (or Power)</td><td rowspan=1 colspan=1>0</td><td rowspan=1 colspan=1>1000 amps</td></tr></table>

3.2.2.9 The administrator shall have the capability to modify the expected range of sensed data against which the data will be validated.

The engineering units of sensed data input to the tool shall comply with the units listed in

3.2.2.10 Table 6 for the associated physical parameter measured prior to input to the diagnostics.

The tool shall provide the capability to convert sensed data not provided in the units listed in

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

Table 6 to the required units.

Table 6. Required engineering units for sensed data.
<table><tr><td rowspan=1 colspan=1>PhysicalParameter</td><td rowspan=1 colspan=1>EngineeringUnits forSensed Data</td></tr><tr><td rowspan=1 colspan=1>Temperature</td><td rowspan=1 colspan=1>Degrees F</td></tr><tr><td rowspan=1 colspan=1>Current</td><td rowspan=1 colspan=1>Amps</td></tr></table>

3.2.2.11 The tool shall associate with each continuous parameter one or more tolerances each corresponding to a different sensitivity level for the tool.

3.2.2.12 Any and all errors associated with obtaining, validating, converting, or storing the sensed data shall be logged as described in subsequent specifications and selected errors shall be reported to the user.

## 3.2.3 Diagnostic Process

The automated diagnostic tool shall detect and identify certain performance and operational faults in chiller and cooling tower subsystems of HVAC units following specified algorithms. In addition, the tool shall be designed to permit expansion of diagnostic analysis to additional subsystems. The faults identified and their causes and sources, shall be saved to permanent storage for subsequent analysis.

3.2.3.1 The tool shall monitor performance and operational parameters listed in Table 7 for chillers and cooling towers and identify the specific faults in the specific fault categories listed in the table.

Table 7. Performance and Operational Parameters Monitored by the Automated Diagnostic Tool and Specific Faults Identified
<table><tr><td rowspan=1 colspan=1>Subsystem(s)</td><td rowspan=1 colspan=1>Monitored Parameter</td><td rowspan=1 colspan=1>Fault Category</td><td rowspan=1 colspan=1>Fault</td></tr><tr><td rowspan=3 colspan=1>Chiller</td><td rowspan=2 colspan=1>Chilled Water SupplyTemperature Maintenance</td><td rowspan=2 colspan=1>Chilled Water Supply Temperature notMaintained Correctly</td><td rowspan=1 colspan=1>The chilled water supplytemperature is too high</td></tr><tr><td rowspan=1 colspan=1>The chilled water supplytemperature is too low</td></tr><tr><td rowspan=1 colspan=1>Chiller Schedule</td><td rowspan=1 colspan=1>Chiller Schedule is Incorrect/inError/Corrupt/Inefficient/not Followed</td><td rowspan=1 colspan=1>The chiller is on when itshould be off. Energy isbeing wasted.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

<table><tr><td rowspan=7 colspan=1></td><td rowspan=2 colspan=1>Compressor Cycling</td><td rowspan=2 colspan=1>Compressor Cycling is Abnormal</td><td rowspan=1 colspan=1>The compressor is cycling ontoo frequently. It is notstaying off for the minimumrequired off time</td></tr><tr><td rowspan=1 colspan=1>The compressor is cycling offtoo frequently. It is notstaying on for the minimumrequired on time</td></tr><tr><td rowspan=2 colspan=1>Compressor and Condenser FanInterlock (for air-cooledcondensers only)</td><td rowspan=2 colspan=1>Compressor is Improperly Interlockedwith Condenser Fan</td><td rowspan=1 colspan=1>The compressor is on whilethe condenser fan is off. Thechiller cannot reject heat andthis could damage thecompressor</td></tr><tr><td rowspan=1 colspan=1>The condenser fan is onwhile the compressor is off.The fan is runningunnecessarily and wastingenergy.</td></tr><tr><td rowspan=3 colspan=1>Compressor and CondenserPump Interlock (for water-cooled condensers only)</td><td rowspan=3 colspan=1>Compressor is Improperly Interlockedwith Condenser Pump</td><td rowspan=1 colspan=1>The compressor is on whilethe condenser pump is off.The chiller cannot reject heatand this could damage thecompressor.</td></tr><tr><td rowspan=1 colspan=1>The condenser pump iscycling unnecessarilyfrequently. Repeatedfrequent cycling will shortenthe life of the condenserpump.</td></tr><tr><td rowspan=1 colspan=1>The condenser pump isturning on too much inadvance of the compressorand wasting energy.</td></tr><tr><td rowspan=5 colspan=1>Cooling Tower</td><td rowspan=2 colspan=1>Cooling Tower Fan Cycling</td><td rowspan=2 colspan=1>Cooling Tower Fan Cycling Problem</td><td rowspan=1 colspan=1>The cooling tower fan is notstaying off long enoughduring cycling.</td></tr><tr><td rowspan=1 colspan=1>The cooling tower fan is notstaying on long enoughduring cycling.</td></tr><tr><td rowspan=2 colspan=1>Sump Temperature Control</td><td rowspan=2 colspan=1>Sump Temperature is ImproperlyControlled</td><td rowspan=1 colspan=1>The cooling tower fan is offbut should be on. As a result,the condenser water is notbeing cooled sufficiently.</td></tr><tr><td rowspan=1 colspan=1>The cooling tower fan is onbut it should be off. Energyis being wasted.</td></tr><tr><td rowspan=1 colspan=1>Cooling Tower Approach</td><td rowspan=1 colspan=1>Cooling Tower Approach Problem</td><td rowspan=1 colspan=1>The cooling tower approachis greater than the ApproachBenchmark provided in setup. Heat rejection from thecooling tower is less thanexpected.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

<table><tr><td rowspan=3 colspan=1></td><td rowspan=2 colspan=1>Cooling Tower Fan Staging</td><td rowspan=2 colspan=1>Cooling Tower Fan Staging Problem</td><td rowspan=1 colspan=1>The Sump temperature isabove the cooling tower fan&quot;on&quot; set point, but all coolingtower fans are not on. Thisindicates a problem with thefan staging and, as a result,the cooling tower is notmaintaining the sumptemperature as low as itshould.</td></tr><tr><td rowspan=1 colspan=1>A fan is on even though thesump temperature is belowthe “off&#x27; set point. Thisindicates a fan stagingproblem, and energy is beingwasted. All cooling towerfans should be off.</td></tr><tr><td rowspan=1 colspan=1>Cooling Tower Range</td><td rowspan=1 colspan=1>Cooling Tower Range Problem</td><td rowspan=1 colspan=1>The cooling tower range isbelow its benchmark. Asresult, heat rejection by thecooling tower is less thanexpected and the coolingtower is performing at lessthan its capacity.</td></tr><tr><td rowspan=3 colspan=1>Chilled WaterLoop</td><td rowspan=2 colspan=1>Supply Fan(s) and the Primary-Loop Chilled Water PumpsInterlock</td><td rowspan=2 colspan=1>Supply Fan(s) and the Primary-LoopChilled Water Pumps are not InterlockedProperly</td><td rowspan=1 colspan=1>The is possibly a problemwith the supply fan control.</td></tr><tr><td rowspan=1 colspan=1>This chilled water pump isbeing operated unnecessarilyand is wasting energy. Thechilled water pump shouldnot operate unless at leastone of the supply fans in anair handling unit served bythe chilled water pump is on.</td></tr><tr><td rowspan=1 colspan=1>Supply Fan(s) and theSecondary-Loop Chilled WaterPumps Interlocked</td><td rowspan=1 colspan=1>Supply Fan(s) and the Secondary-LoopChilled Water Pumps are not InterlockedProperly.</td><td rowspan=1 colspan=1>Possible problem withsecondary chilled waterpump control—check to seeif loads in the spaces servedare being met for all supplyfans that are part of airhandlers served by thissecondary chilled water loopand that is on when thesecondary chilled waterpump is off.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

<table><tr><td rowspan=2 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>The secondary chilled waterpump and some of the supplyfans that are served by it arenot interlocked properly.This secondary chilled waterpump is operatingunnecessarily when allsupply plans it serves are offand, as a result, is wastingenergy. The secondarychilled water pump shouldnot operate unless at leastone of the supply fans in anair handler served by thispump is on.</td></tr><tr><td rowspan=1 colspan=1>Secondary and Primary LoopChilled Water Pumps Interlock</td><td rowspan=1 colspan=1>Secondary and Primary Loop ChilledWater Pumps are not InterlockedProperly</td><td rowspan=1 colspan=1>The secondary chilled waterpumps that are on arewasting energy. Secondarychilled water pumps shouldonly operate when theprimary CHW pump isoperating.</td></tr><tr><td rowspan=2 colspan=1>Chiller/C oolingTower</td><td rowspan=2 colspan=1>Cooling Tower Fan(s) andCondenser Pump Interlock</td><td rowspan=2 colspan=1>Cooling Tower Fan(s) and CondenserPump are not Interlocked Properly</td><td rowspan=1 colspan=1>The cooling tower fan andcondenser pump are notinterlocked properly. Energyis being wasted because thecooling tower fan should beoff when the condenser pumpis not operating.</td></tr><tr><td rowspan=1 colspan=1>The interlock between thecondenser pump and thecooling tower may not beproperly implemented. Thecooling tower fan may be offwhen the condenser pump isrunning, but this should notalways be the case.</td></tr><tr><td rowspan=2 colspan=1>Chiller/WaterLoop</td><td rowspan=2 colspan=1>Compressor and Primary ChilledWater Pump(s) Interlock</td><td rowspan=2 colspan=1>Compressor and Primary Chilled WaterPump(s) are not Interlocked Properly</td><td rowspan=1 colspan=1>The primary chilled waterpumps are not interlockedproperly with thecompressor. The condenserpump is cycling on and offunnecessarily. Repeatedfrequent cycling will shortenthe life of the pump.</td></tr><tr><td rowspan=1 colspan=1>The compressor is notproperly interlocked with theprimary chilled water pumps.The chiller is operatingwithout a load. Energy isbeing wasted and damage tothe compressor may result.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

<table><tr><td></td><td></td><td></td><td>The compressor is not properly interlocked with the primary chilled water pumps. Water side economizing is not being used, and the primary chilled water pumps are cycling on too much in advance of the compres sor and wasting energy.</td></tr></table>

3.2.3.2 With each fault identified in Table 7, the tool shall associate text describing the possible problem, causes, and a recommended fix. This text for each fault is listed in Table $8 _ { \pm }$

Table 8 Text to Associate with Each Anomaly Detected
<table><tr><td rowspan=1 colspan=1>Subsystem(s)</td><td rowspan=1 colspan=1>Fault Category</td><td rowspan=1 colspan=1>Fault/PossibleProblem</td><td rowspan=1 colspan=1>Causes</td><td rowspan=1 colspan=1>Fix</td></tr><tr><td rowspan=4 colspan=1>Chiller</td><td rowspan=2 colspan=1>Chilled Water SupplyTemperature not MaintainedCorrectly</td><td rowspan=1 colspan=1>The chilled watersupply temperature istoo high</td><td rowspan=1 colspan=1>1) Chilled watersupply temperatureset point is set toohigh. 2) Chillerload exceedscapacity.</td><td rowspan=2 colspan=1></td></tr><tr><td rowspan=1 colspan=1>The chilled watersupply temperature istoo low</td><td rowspan=1 colspan=1>1) Chilled watersupply temperatureset point is lowerthan necessary.</td></tr><tr><td rowspan=1 colspan=1>Chiller Schedule isIncorrect/inError/Corrupt/Inefficient/notFollowed</td><td rowspan=1 colspan=1>The chiller is on when itshould be off. Energy isbeing wasted.</td><td rowspan=1 colspan=1>Incorrectlyspecified schedule.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Compressor Cycling isAbnormal</td><td rowspan=1 colspan=1>The compressor iscycling on toofrequently. It is notstaying off for theminimum required offtime.</td><td rowspan=1 colspan=1>1) Incorrectlyspecified minimumoff time in the set-up of thisdiagnostic, 2)Incorrectlyspecified minimumoff time in thecontrol algorithmfor the compressor,3) a failed relay ormis -adjusted relay,for compressorshaving theminimum off timecontrolled by arelay.</td><td rowspan=1 colspan=1></td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

<table><tr><td rowspan=4 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>The compressor iscycling off toofrequently. It is notstaying on for theminimum required ontime.</td><td rowspan=1 colspan=1>1) Incorrectlyspecified minimumon time in the set-upof this diagnostic, 2)Incorrectlyspecified minimu moff time in thecontrol algorithmfor the compressor,3) a failed relay ormis -adjusted relay,for compressorshaving theminimum on timecontrolled by arelay.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=2 colspan=1>Compressor is ImproperlyInterlocked with CondenserFan (for air-cooledcondensers only)</td><td rowspan=1 colspan=1>The compressor is onwhile the condenser fanis off. The chiller cannotreject heat and this coulddamage the compressor</td><td rowspan=1 colspan=1>The compressor ison while thecondenser fan is off.The interlockbetween thecompressor andcondenser fan in thecontrol code is notspecified correctlyor is overridden.</td><td rowspan=2 colspan=1></td></tr><tr><td rowspan=1 colspan=1>The condenser fan is onwhile the compressor isoff. The fan is runningunnecessarily andwasting energy.</td><td rowspan=1 colspan=1>The condenser fanis running while thecompressor is off.This wastes energy.The interlockbetween thecompressor andcondenser fan in thecontrol code is notspecified correctlyor is overridden.</td></tr><tr><td rowspan=1 colspan=1>Compressor is ImproperlyInterlocked with CondenserPump (for water-cooledcondensers only)</td><td rowspan=1 colspan=1>The compressor is onwhile the condenserpump is off. The chillercannot reject heat andthis could damage thecompressor.</td><td rowspan=1 colspan=1>The compressor ison while thecondenser pump isoff. The interlockbetween thecompressor andcondenser pump inthe control code isnot specifiedcorrectly or isoverridden.</td><td rowspan=1 colspan=1></td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

<table><tr><td rowspan=2 colspan=1></td><td rowspan=2 colspan=1></td><td rowspan=1 colspan=1>The condenser pump iscycling unnecessarilyfrequently. Repeatedfrequent cycling willshorten the life of thecondenser pump.</td><td rowspan=1 colspan=1>The CondenserPump is turning onand off toolfrequently.</td><td rowspan=2 colspan=1></td></tr><tr><td rowspan=1 colspan=1>The condenser pump isturning on too much inadvance of thecompressor and wastingenergy.</td><td rowspan=1 colspan=1>The CondenserPump MaximumStart-Up time is notspecified correctlyor is overridden inthe control code.</td></tr><tr><td rowspan=3 colspan=1>Cooling Tower</td><td rowspan=2 colspan=1>Cooling Tower Fan CyclingProblem</td><td rowspan=1 colspan=1>The cooling tower fan isnot staying off longenough during cycling.</td><td rowspan=1 colspan=1>1) The timer that isintended toeliminate shortcycling is notworking. 2) The&quot;on&quot; and &quot;off&quot;control set pointsfor the coolingtower fan are tooclose to oneanother.</td><td rowspan=2 colspan=1></td></tr><tr><td rowspan=1 colspan=1>The cooling tower fan isnot staying on longenough during cycling.</td><td rowspan=1 colspan=1>1) The timer that issupposed toeliminate shortcycling is notworking properly.2) The &quot;on&quot; and&quot;off&quot; control setpoints for the fanare too close to oneanother. 3) Thecooling towercapacity is too greatfor the load, so thefans rapidly cycleoff (i.e., the on timeis very short)because the load ismet quickly.</td></tr><tr><td rowspan=1 colspan=1>Sump Temperature isImproperly Controlled</td><td rowspan=1 colspan=1>The cooling tower fan isoff but should be on. Asa result, the condenserwater is not being cooledsufficiently.</td><td rowspan=1 colspan=1>1) a cooling towercontrol problem, 2)sump temperaturesensor problem, 3)electrical problemssuch as a motorfailure, 4) otherproblems with thefan motor.</td><td rowspan=1 colspan=1></td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

<table><tr><td colspan="1" rowspan="4"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">The cooling tower fan ison but it should be off.Energy is being wasted.</td><td colspan="1" rowspan="1">1) a cooling towercontrol problem, 2)an actuator or relayhas failed.</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">Cooling Tower ApproachProblem</td><td colspan="1" rowspan="1">The cooling towerapproach is greater thanthe ApproachBenchmark provided inset up. Heat rejectionfrom the cooling tower isless than expected.</td><td colspan="1" rowspan="1">1) The coolingtower media isfouled due tomineral deposits orambient dirt, dust,or othercontaminants.2) Restrictedairflow for otherreasons (e.g., pieceof cardboard stuckover part of coolingtower air inlet). 3)There is condenserpump fouling, pipefouling, or otherrestrictions on thewater side.</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="2">Cooling Tower Fan StagingProblem</td><td colspan="1" rowspan="1">The Sump temperature isabove the cooling towerfan “"on" set point, but allcooling tower fans arenot on. This indicates aproblem with the fanstaging and, as a result,the cooling tower is notmaintaining the sumptemperature as low as itshould.</td><td colspan="1" rowspan="1">1) Different valuesof the fan “on" setpoint are specifiedin the fan controllerand this software.2) Fan stagingcontrol algorithm isnot correctlyspecified. 3) A fanmotor or electricalconnection hasfailed. 4) Thesump temperaturesensor has failed oris out of calibration.</td><td colspan="1" rowspan="2"></td></tr><tr><td colspan="1" rowspan="1">A fan is on even thoughthe sump temperature isbelow the “off' setpoint. This indicates afan staging problem,and energy is beingwasted. All coolingtower fans should beoff.</td><td colspan="1" rowspan="1">1) Different valuesof the fan "off' setpoint are specifiedin the fan controllerand this software.2) Fan stagingcontrol algorithm isnot correctlyspecified. 3) Thesump temperaturesensor has failed oris out of calibration.</td></tr><tr><td colspan="1" rowspan="1">Automated Diagnostics</td><td colspan="1" rowspan="1">Version:      1.1</td></tr><tr><td colspan="1" rowspan="1">Software Requirements Specification</td><td colspan="1" rowspan="1">Date: 8/28/2003</td></tr><tr><td colspan="5" rowspan="1">Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

<table><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Cooling Tower RangeProblem</td><td colspan="1" rowspan="1">The cooling tower rangeis below its benchmark.As result, heat rejectionby the cooling tower isless than expected andthe cooling tower isperforming at less thanits capacity.</td><td colspan="1" rowspan="1">1) Tower mediamay be fouled dueto mineral depositsor ambient dirt,dust, or othercontaminants.2) the airflow isrestricted by someother obstruction.3) The condenserpump is fouling,pipes are fouling, orthere are otherwater-side flowrestrictions. 4) Thecooling tower is toosmall for the load(i.e., there is adesign problem)</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="2">Chilled WaterLoop</td><td colspan="1" rowspan="2">Supply Fan(s) and thePrimary-Loop Chilled WaterPumps are not InterlockedProperly</td><td colspan="1" rowspan="1">The is possibly aproblem with the supplyfan control.</td><td colspan="1" rowspan="1">The chilled waterpump is off and thesupply fan for atleast one air handlerserved by this pumpis on. There may bea problem with thecontrol of thissupply fan or otherparts of the airhandlers withsupply fansoperating underthese conditions.</td><td colspan="1" rowspan="2"></td></tr><tr><td colspan="1" rowspan="1">This chilled water pumpis being operatedunnecessarily and iswasting energy. Thechilled water pumpshould not operateunless at least one ofthe supply fans in an airhandling unit served bythe chilled water pumpis on.</td><td colspan="1" rowspan="1">Improper interlockbetween the chilledwater pump and thesupply fans.</td></tr><tr><td colspan="1" rowspan="1">Automated Diagnostics</td><td colspan="1" rowspan="1">Version:      1.1</td></tr><tr><td colspan="1" rowspan="1">Software Requirements Specification</td><td colspan="1" rowspan="1">Date: 8/28/2003</td></tr><tr><td colspan="5" rowspan="1">Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

<table><tr><td rowspan=3 colspan=1></td><td rowspan=2 colspan=1>Supply Fan(s) and theSecondary-Loop ChilledWater Pumps are notInterlocked Properly.</td><td rowspan=1 colspan=1>Possible problem withsecondary chilled waterpump control—check tosee if loads in the spacesserved are being met forall supply fans that arepart of air handlersserved by this secondarychilled water loop andthat is on when thesecondary chilled waterpump is off.</td><td rowspan=1 colspan=1>Improper interlockbetween thesecondary chilledwater pump and thesupply fans of airhandlers it serves.</td><td rowspan=2 colspan=1></td></tr><tr><td rowspan=1 colspan=1>The secondary chilledwater pump and someof the supply fans thatare served by it are notinterlocked properly.This secondary chilledwater pump is operatingunnecessarily when allsupply plans it servesare off and, as a result,is wasting energy. Thesecondary chilled waterpump should notoperate unless at leastone of the supply fansin an air handler servedby this pump is on.</td><td rowspan=1 colspan=1>Improper interlockbetween thesecondary chilledwater pump and thesupply fans of airhandlers it serves</td></tr><tr><td rowspan=1 colspan=1>Secondary and Primary LoopChilled Water Pumps are notInterlocked Properly</td><td rowspan=1 colspan=1>The secondary chilledwater pumps that are onare wasting energy.Secondary chilled waterpumps should onlyoperate when the primaryCHW pump is operating</td><td rowspan=1 colspan=1>Improper interlockbetween thesecondary chilledwater pump and thesupply fans of airhandlers it serves.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Chiller/CoolingTower</td><td rowspan=1 colspan=1>Cooling Tower Fan(s) andCondenser Pump are notInterlocked Properly</td><td rowspan=1 colspan=1>The cooling tower fanand condenser pump arenot interlocked properly.Energy is being wastedbecause the coolingtower fan should be offwhen the condenserpump is not operating.</td><td rowspan=1 colspan=1>The cooling towerfan and condenserpump are notinterlockedproperly.</td><td rowspan=1 colspan=1></td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

<table><tr><td>Chiller/Water Loop</td><td>Compressor and Primary</td><td>the condenser pump and the cooling tower may not be properly implemented. The cooling tower fan may be off when the condenser pump is running, but this should not always be the case. The primary chilled</td><td>The cooling tower fan and condenser pump may not be interlocked properly. The chilled water</td><td></td></tr><tr><td rowspan="3"></td><td>Chilled Water Pump(s) are not Interlocked Properly</td><td>water pumps are not interlocked properly with the compressor. The condenser pump is cycling on and off unnecessarily. Repeated frequent cycling will shorten the life of the pump. The compressor is not properly interlocked</td><td>pump is cycling between on and off while the compressor is off. The primary chilled water pumps are not interlocked properly with the compressor. The compressor is running while the primary chilled</td><td></td></tr><tr><td></td><td>without a load. Energy is being wasted and damage to the compressor may result.</td><td>not properly interlocked with the primary chilled water pumps. The primary chilled</td><td></td></tr><tr><td></td><td>with the primary chilled water pumps. Water side economizing is not being used, and the primary chilled water pumps are cycling on</td><td>water pumps are cycling on too much in advance of the compressor turning on.</td><td></td></tr></table>

3.2.3.3 The tool shall be designed to permit the addition of diagnostic algorithms for other subsystems of HVAC units.

3.2.3.4 A diagnostic algorithm shall not process if any input data to the algorithm is missing. The user shall be notified if a diagnostic algorithm cannot process due to missing data.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

3.2.3.5 Any and all errors associated with failures of the diagnostic algorithms shall be logged as described in subsequent specifications and selected errors shall be reported to the user.

3.2.3.6 The tool shall monitor the unit under diagnosis, either in real time or batch mode, for an indefinite period of time or until input data are no longer available, and log diagnostic results as they are determined.

3.2.3.7 Diagnostic results that are saved to permanent storage shall be accompanied in storage by the absolute time of occurrence, the identity of the unit to which the diagnostic applies, and the identity of the diagnostic.

3.2.3.8 The administrator user shall have the capability to adjust the sensitivity of the diagnostic analysis in order to increase or decrease the probability of fault detection.

## 3.2.4 Output Processing

The automated diagnostic tool shall display and record diagnostic results. Diagnostic results to be displayed to the user will be done so in a simple, graphical and textual format. Diagnostic results shall also be saved to permanent storage for subsequent retrieval, display, and analysis.

3.2.4.1 The administrator shall have the ability to specify which diagnostic results will not be reported in any manner, i.e., not detected.

3.2.4.2 The display of each diagnostic result for fault conditions will include a description of the fault, potential causes of the fault, the location of the fault, and the absolute time of occurrence.

## 3.3 Usability

This section describes requirements related to the usability of the tool.

## 3.3.1 User Interface

The following specifies usability requirements for the user interface.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

3.3.1.1 The area on the main, systems, and condition windows sensitive to the users selection device, typically the mouse, shall include the line surrounding the item of interest over the entire width of the window. This includes the diagnostic indicators.

3.3.1.2 The windows listing diagnostic results shall increase in height as needed to display entries up to a maximum of ten entries. Once the window has reached maximum size and there are additional items to display, the window shall deploy a scroll bar to permit the user to scroll through the additional entries. In this event, a summary set of diagnostic indicators shall appear above (below) the top (bottom) entry in the display. This set(s) of indicators shall summarize diagnostic indicators not currently appearing on the list above (below) it. An indicator in the summary set shall be active if any similar indicator not appearing above (or below) it is active. The summary set indicators comply with the same specification for activation as other indicators (see 3.5.1.39).

3.3.1.3 The building, subsystems, and condition windows shall display the current time if the diagnostic tool is operating in real time. If the tool is operating in batch mode, the time displayed will be the time associated with the entry currently being processed in the batched input.

3.3.1.4 If only a single building is defined, the subsystems window shall become the main window of the application and shall have all the functionality of the main window as described in these specifications.

3.3.1.5 Each window of the diagnostic tool shall display an animated graphical feature indicating the status, whether active or not, of the diagnostic processing.

3.3.1.6 The subsystem window shall be modal to the building window, the condition window modal to the subsystem window, and the diagnostic history and diagnostic information windows shall be modal to the condition window.

## 3.4 Supportability

This section describes requirements related to the support of the software after initial installation.

## 3.4.1 Error Reporting

Significant errors in software operation shall be logged to permanent storage with sufficient detail to guide the administrator and to assist support staff in locating and rectifying the error. In addition, selected errors shall be reported to the user.

3.4.1.1 Software errors logged to permanent storage shall include the absolute time of occurrence, the name of the software module in which the error occurred, the name of the software function in which the error occurred, and a description of the error.

## 3.5 Interfaces

This section describes requirements related to interfaces of the tool.

## 3.5.1 User Interfaces

This section describes the specifications for the user interface.

3.5.1.1 The user interface shall consist of six windows: Main window, configuration window, subsystems window, condition window, diagnostic information window, and diagnostic history window.

3.5.1.2 These windows shall be organized in a hierarchy enforcing a navigational order on the user. This hierarchy is depicted in Figure 4. As indicated in the figure, the main window is at the top of the hierarchy and is the first window that appears when the tool begins execution. The configuration window is subordinate to the main window and can only be displayed by a user selection on the main window. The third window in the hierarchy is the subsystems window and it can only be displayed by a user selection on the main window. The fourth window in the hierarchy is the condition window and it can only be displayed by a user selection on the subsystems window. The fifth window is the diagnostic information window. This window can only be displayed by a user selection on the condition window or by a user selection on the diagnostic history window if it is displayed. The diagnostic history window can only be displayed by a user action on the diagnostic information window.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

![](images/bdfe4c5812346174e49fe9fc5b46bb6b669780ff04f0eda13dc8fc3df33220cf.jpg)  
Figure 4 User Interface Window Hierarchy

3.5.1.3 The main (e.g., initial or default) window shall list buildings monitored and summarizing the current diagnostic status of all contained monitored units. A recommended layout for this window is presented in Figure 5. This window shall be titled “Diagnostician”.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

![](images/e8270b2d4ba43e2d0f5a19311971a9c5e95b9ea445f8d3f06f65891702b49fe1.jpg)  
Figure 5 Recommended Layout for Main Window

<table><tr><td>3.5.1.4The main window shall have main menus entitled “File” and &quot;Status&quot;</td><td></td><td></td><td></td><td></td></tr><tr><td></td><td>&quot;Configure Diagnostics&quot;, “Logout&quot;, “Exit&quot;.</td><td>3.5.1.5The main menu entitled “File” shall contain the following menu items in the following order:</td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td></tr><tr><td>&quot;Start Diagnostics”, “Stop Diagnostics&quot;.</td><td></td><td></td><td>3.5.1.6The main menu entitled “Status” shall contain the following menu items in the following order:</td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td>3.5.1.7The menu items named “Configure Diagnostics” and “Exit” in the main menu entitled “File” sha</td><td></td><td></td><td></td></tr><tr><td>be enabled at all times.</td><td></td><td></td><td></td><td></td></tr><tr><td>3.5.1.8The menu item named “Logout&quot; in the main menu entitled “File” shall be enabled only if the</td><td></td><td></td><td></td><td></td></tr><tr><td>current user is presently authenticated as the administrator user. Otherwise, this menu item shall be</td><td></td><td></td><td></td><td></td></tr><tr><td>disabled.</td><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td>3.5.1.9The menu item named “Start Diagnostics” in the main menu entitled “Status” shall be enabled</td><td></td><td></td><td></td></tr><tr><td></td><td>only if diagnostic processing is not currently running. Otherwise. the menu item shall be disabled.</td><td></td><td></td><td></td></tr><tr><td>3.5.1.10</td><td></td><td></td><td></td><td></td></tr><tr><td></td><td>The menu item named “Stop Diagnostics” in the main menu entitled “Status” shall be</td><td></td><td></td><td></td></tr><tr><td></td><td>enabled only if diagnostic processing is currently running. Otherwise. the menu item shall be disabled.</td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td></tr><tr><td>3.5.1.11</td><td></td><td></td><td></td><td></td></tr><tr><td></td><td>Selecting the “Configure Diagnostics” menu item of the main menu entitled “File” shall</td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td>display the configuration window. making it the current window. modal to the main window.</td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td></tr></table>

3.5.1.12 The configuration window shall permit the administrator user to modify the following parameters:

a. The password for the administrator user.

b. A toggle enabling or disabling the main window of the tool as a screen saver.

c. A toggle enabling or disabling the main window’s position on the screen as the top most window.

d. Buildings and subsystems to be monitored and the conditions they will be monitored

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

for. The conditions will be selected from a list provided by the tool.

e. The enabled state of individual conditions. Disabled conditions will not be processed or displayed.

f. The sensitivity of each condition by selecting a sensitivity from a list provided by the tool.

g. Scale factors for transforming the engineering units of sensed input data to the required units.

h. The expected range of sensed input data.

3.5.1.13 The configuration window shall display the following non-modifiable information: a.

3.5.1.14 The configuration window shall have a button labeled “Save” that when clicked will present the user with a window by which to enter a disk file or database name in which to save the modifiable data in the window. Entering a file name shall cause the permanent storage of the modified parameters and their immediate use by the diagnostic operations after confirmatory responses by the user. If the user does not confirm the request to save, it will not be performed. If the user does not confirm the request to relay the modified parameters to the diagnostic processing immediately, it will not be performed. In either event, the configuration window will remain displayed.

3.5.1.15 The configuration window shall have a button labeled “Close” that will dismiss the configuration window and return the user to the main window. If the user has made changes to data in the configuration window, the tool will request confirmation of the user’s desire to dismiss the window. If the user does not confirm the request, the window will not be dismissed.

3.5.1.16 The configuration window shall have a button labeled “Recall” that will permit the user to recall a disk file of previously saved parameters from which to populate the configuration window. When functioning as a screen saver, the window shall change location on the screen periodically and will continue to be updated by diagnostic results.

3.5.1.17 The subsystems window shall list subsystems monitored for a specific building and summarizing the current diagnostic status of all monitored subsystems. A recommended layout for this window is presented in Figure 6.

![](images/5502fdd9b598148d442b17fcb00449d06a1df25a6a15204e5fcb027460dfd23d.jpg)  
Figure 6 Recommended Layout for Systems Window

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

3.5.1.18 The condition window shall list the current status of all diagnostics for a specific subsystem. A recommended layout for this window is depicted in Figure 7.

![](images/6c4a49546e8dd576ff4c54844180f0d603f958a455b1e8ef303c374d480c9d4d.jpg)  
Figure 7 Recommended Layout for Condition Window

3.5.1.19 The diagnostic information window shall provide a detailed description of the diagnostic.   
A recommended layout for this window is depicted in Figure 8.

![](images/0811e4987e9aba51c92f073011b661f39532f63ee9daad4e56dcaa03cd2e6588.jpg)  
Figure 8 Recommended Layout for Diagnostic Information Window

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

3.5.1.20 The diagnostic information window shall have a button labeled “Print” that when clicked will display a window listing items to print including the diagnostic information window, the history window, and both the diagnostic and history windows. The user selects the item of interest and clicks the “OK” button to print the selection, an image(s) of the item(s) selected.

3.5.1.21 The diagnostic information window shall include the following information regarding the diagnostic:

1. A description of the possible problem.

2. Potential causes.

3. Fixes.

3.5.1.22 The diagnostic information window shall have a button labeled “Close” that shall dismiss the window.

3.5.1.23 The diagnostic information window shall have a button labeled “History” that when clicked will display the diagnostic history window and display the previous week’s diagnostic results.

3.5.1.24 The diagnostic history window shall display historical diagnostic results for a specific diagnostic. A recommended layout for this window is depicted in Error! Reference source not found.. This figure includes a color map that provides a graphical indication of diagnostic condition.

![](images/48ca0b9245602d4da263af1fe5b43c5604eb9320ebbe3014ca4007c563e3aaba.jpg)  
Figure 9 Recommended Layout for Diagnostic History Window

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

3.5.1.25 The diagnostic history window shall provide user selections for start times and end times for the history interval. These selections shall be in the form of a calendar control.

3.5.1.26 The smallest time interval displayed by the diagnostic history window is one week.

3.5.1.27 The longest time interval that may be displayed by the diagnostic history window is two years.

3.5.1.28 The color map of the history window shall indicate confirmed faults with the color red, potential faults with the color yellow, normal conditions with the color green, and periods when diagnostic processing was not active with the color gray. Diagnostic processing should be assumed inactive between periods of time when no confirmed fault, potential fault, or normal condition has been recorded.

3.5.1.29 The vertical axis of the color map of the history window shall indicate hour of the day and the horizontal axis shall indicate the absolute date and the day of week.

3.5.1.30 The diagnostic history window shall have a button labeled “Print” that when clicked will display a window listing items to print including the diagnostic information window, the history window, and both the diagnostic and history windows. The user selects the item of interest and clicks the “OK” button to print the selection, an image(s) of the item(s) selected.

3.5.1.31 The diagnostic history window shall have a button labeled “Close” that will dismiss the window.

3.5.1.32 The subsystems window, condition window, and diagnostic information window shall display a title that indicates its specific location or absolute path in the navigation hierarchy of windows. This title shall be a concatenation of the title of the previous window displayed, not including the diagnostic history window, and the name of the entry selected to obtain the current window. The two parts of the title shall be separated by a dash surrounded by a single space.

3.5.1.33 The main window, subsystems window, condition window, and diagnostic information window shall display the appropriate time below the title as specified in 3.3.1.3.

3.5.1.34 The main window, subsystems window, and condition window shall have three diagnostic indicators for each item listed.

3.5.1.35 One indicator shall be active when no diagnostic conditions exists. This indicator shall be designated the “OK” indicator and shall appear green when active.

3.5.1.36 One indicator shall be active when a potential diagnostic condition exists. This indicator shall be designated the “Caution” and shall appear yellow when active.

3.5.1.37 One indicator shall be active when a confirmed diagnostic condition exists. This indicator shall be designated the “Not OK” indicator and shall appear red when active.

3.5.1.38 Only one indicator shall be active at a given time for a specific diagnostic and no indicators shall flash when active.

3.5.1.39 The diagnostic indicators on the main window and subsystems window shall summarize all diagnostic conditions associated with each entry in the window. In general, an active “OK” indicator indicates no positive diagnostic results currently exist within the building or subsystem, as applicable for the window. An active “Caution” indicator indicates that at least one potential problem currently exists within the building or subsystem, as applicable, and no confirmed problem currently exists. An active “Not OK” indicator indicates at least one confirmed problem exists regardless of whether cautionary or non-positive results exist. Essentially, confirmed problems override potential problem indications which override non-positive results.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.6 Security

Certain functions of the tool directly available to the user require the user to possess supplementary privileges associated with performing these functions. These supplementary privileges are possessed by the administrator user and are in addition to those of the general user as described in 2.5. The tool determines the type of user by requesting an identifier and password from the user. The requirements related to this process are discussed in other requirements in this document.

## 3.7 Other Requirements

The tool shall log to permanent storage the occurrence of changes to the fixed data. The log shall indicate the time and date of the change, original value of the item(s) changed, and the new value of the item(s) changed.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

4. Appendix A: Data Flow Diagrams of Diagnostic Processes for Chillers, Cooling Towers, and Chilled-Water Distribution

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

Context Diagram Diagnose Chiller/Cooling Tower

![](images/a076fd93213777fdc5d6cfc2a7165ed0f0a22ce027ef968bc49c6967858b81b6.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 0.0 Diagnose Chiller/Cooling Tower

![](images/c7053fd2a1ef48e88b0cb2c6d2f0652d7f0beab4febf1e2b2ca785ead4d3687b.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 0.0 Diagnose Chiller/Cooling Tower

![](images/6ec0627723ea2a82873ceb474be217ec9c0a48b3237f1dd504b493b34b90cf24.jpg)  
Battelle Northwest, 2003

Page 42

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.0 Diagnose Chiller

![](images/15ed49a1d4ac94fe4798e98182e341ddd1e8bd6f9ecb2e9d8e1dc7e3a211c9d1.jpg)  
Battelle Northwest, 2003  
Page 43

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

1.1 Diagnose Chiller Schedule

![](images/720508dc0ec6761f1421f2ea147644ecb35518898c53b815edd859126c4ed317.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.1.1 Evaluate Compressor Power vs. Time

Compare the current time to the scheduled time for the chiller to be on.,   
If the current time is a scheduled chiller "on" time, then stop--make no further check. OK.   
If the current time is outside the scheduled chiller "on" times (i.e., the chiller should be off),   
then check if the Compressor $\mathsf { S t a t u s } = \ " { \mathrm { { \Omega } } } { \mathrm { { \Omega } } } { \mathrm { { \Omega } } } ^ { \prime }$   
If the Compressor Status $, = " \mathrm { O } \mathsf { f f } , "$ then the chiller is off as it should be and it is OK.   
Set Chiller Schedule $\mathsf { O K / N o t } = \ " \mathrm { O K } ^ { \prime \prime } .$   
If the Compressor $\mathsf { S t a t u s } = \mathsf {" O n } ,$ " then the Chiller is "On" when it should be off. Not   
OK. Energy is being wasted. Set Chiller Schedule ${ \mathsf { O K } } / { \mathsf { N o t } } = " { \mathsf { N o t } } { \mathsf { O K } } "$

Note: The purpose of this process is to determine if the chiller is on when it is supposed to be off.

Ref. File: 1.2 Chiller schedule diagnostics.doc

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

1.2 Check Chilled Water Control

![](images/76fe149afe52b2bd524e47b392fb14ab1c2cc9447f54789abdcbebf03f74d188.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.2.1 Filter (pass) CHWST Steady State "On" Only

If Compressor State = "Steady", then pass values of CHWST.   
Label these passesd values CHWST Steady State CHW.

If Compressor State = "Transient" or Compressor State = "Off", then reject values of CHWST.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.2.2 Evaluate Steady-State CHWST Control

![](images/e1a6a3628e4c1a525086984a9464e6513927e4671f43bc98a50f6909d8ae9d01.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

# 1.2.2.1 Evaluate CHWST Variation at Single Points

Calculate the upper bound for acceptable Chilled Water Temperature using

CHWST Upper Bound = CHW Setpoint + (CHWdUp)

Calculate the acceptable lower bound for the Chilled Water Temperature using

CHWST Lower Bound = CHW Setpoint - (CHWdDown).

Compare the Chilled Water Supply Temperature (CHWST) for steady state to the CHWST Upper Bound and CHWST Lower Bound.

If CHWST Steady State CHW > CHWST Upper Bound, then   
set CHWST Maintained OK/not = "Too high" for the current time.   
If CHWST Steady State CHW <= CHWST Upper Bound   
and CHWST Steady State CHW>= CHW Lower Bound, then   
set CHWST Maintained OK/not = "OK" for the current time.   
If CHWST Steady State CHW < CHWST Lower Bound, then   
set CHWST Maintained OK/not = "Too low" for the current time.

Calculate the CHW Temperature Deviation for a single point (current time)

CHWST Deviation = CHWST Steady State CHW - CHW Setpoint.

Ref file: 2.1CHW temperature control.doc

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

1.2.2.2 Evaluate CHWST Variation Alarm Conditions

![](images/64bc1eca6e74b73e19faafd2efd17be9ad3b8f4861ff8f8792cb18bc40cf145e.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.2.2.2.1 Update CHWST Alarm Variables

Update the variable CHWST Maintained OK/not Array

Update all values in the array, adding the current value of CHWST Maintained OK/not to the array and by dropping the oldest value of CHWST Maintained OK/not from the array.

Update values for CHWSTNumber High and CHWSTNumber Low.

Set CHWSTNumber High = number of values "Too High" appearing in CHWST Maintained OK/not Array.

Set CHWSTNumber Low = number of values "Too Low" appearing in CHWST Maintained OK/not Array.

[Determine whether this evaluation should be done during initial start-up processing (this shouldn't really be part of the DFDs because it represents intialization and control),

If Total Number of Time Steps Processed < CHWST Alarm Evaluation Interval, then terminate processing of 2.8.2 (i.e., do not evaluate CHWST Variation Alarm Conditions).

Otherwise, continue with 2.8.2 processing.]

Ref file: 2.1CHW temperature control.doc

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.2.2.2.2 Evaluate Alarm Conditions

Calculate values for CHWSTFraction High and CHWSTFraction Low.

```swift
CHWSTFraction High = CHWSTNumber High/(CHWST Alarm Evaluation Interval)
```

CHWSTFraction Low = CHWSTNumber Low/(CHWST Alarm Evaluation Interval)

Compare CHWSTFraction High with CHWST Alarm Trigger High.   
Compare CHWSTFraction Low with CHWST Alarm Trigger Low.

If CHWSTFraction High >= CHWST Alarm Trigger High, then   
set CHWST Alarm = "Too High."   
If CHWSTFraction High < CHWST Alarm Trigger High and CHWSTFraction Low < CHWST   
Alarm Trigger Low, then   
set CHWST Alarm = "OK".   
If CHWSTFraction Low >= CHWST Alarm Trigger Low, then   
set CHWST Alarm = "Too Low."

Notes: Conclusions regarding a fault existing or not based on individual points are likely to be unrealiable. Conclusions are likely to best be made by considering a high percentage of points over some period of time exceeding some minimum time, e.g., a day or a week (24 hours or 168 hours). Therefore, we base the assignment of CHWST Alarm on a minimum set of points rather than individual points.

Ref file: 2.1CHW temperature control.doc

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.2.2.3 Determine CHWST Statistics\*

If CHWSTAlarm = Too High, then

Calculate mean CHWST for the times correspoding to the too-high points in the CHWST Maintained OK/not Array.

CHWST Mean Too-High Deviation = Sum [CHWST Deviation(time index)]/ (CHWSTNumber High),

where time index takes values between the currrent time and (CHWST Alarm Evaluation Interval - 1) time steps ago and the sum only includes values of CHWST Deviation for which CHWST Maintained OK/not = "Too High".

Set Mean Too Low CHWST Deviation = null.

If CHWSTAlarm = Too Low, then

Calculate mean CHWST for the times correspoding to the too-low points in the CHWST Maintained OK/not Array.

$$
\begin{array} { r l r l } { \mathsf { C H W S T M e a n ~ T o o - L o w ~ D e v i a t i o n } = } & { } & { \mathsf { S u m ~ [ C H W S T ~ D e v i a t i o n ( t i m e ~ i n d e x ) ] } / } \\ & { } & & { ( \mathsf { C H W S T N u m b e r \mathsf { L o w } } ) , } \end{array}
$$

where time index takes values between the currrent time and (CHWST Alarm Evaluation Interval - 1) time steps ago and the sum only includes values of CHWST Deviation for which CHWST Maintained OK/not = "Too Low".

Set Mean Too High CHWST Deviation = null.

Note: This process is proposed for Round 2. Also, additional or other statistics could be calculated in this process. These should also be proposed for Round 2.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.3 Diagnose Chiller Cycling

![](images/d8d9b7feadb1473ce34f9e8c7e80fd9a9ffff3dfb7dd62873145048e1dc826e7.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.3.1 Evaluate Compressor current (or power) vs time

If Compressor Status = "On" and Last Compressor Status = "On", then terminate this evaluation. Nothing new to check.

If Compressor Status = "On" and Last Compressor Status = "Off," then set Last Compressor Switch On Time = Current Time and check Last Compressor Off Interval.

Calculate the Last Compressor Off Interval using

Last Compressor Off Interval = Last Compressor Switch On Time - Last Compressor Switch Off Time

If Last Compressor Off Interval >= Minimum Compressor Off Time, then set Compressor Off Cycle OK/not = "OK."

If Last Compressor Off Interval < Minimum Compressor Off Time, then set Compressor Off Cycle OK/not = "not OK." The compressor is not staying off long enough during cycling. Possible causes include an incorrectly specified minimum off time in the control algorithm or for compressors with minimum on/off times controlled by a relay a failed relay or one requiring adjustment.

If Compressor Status = "Off" and Last Compressor Status = "Off," then terminate this evaluation. Nothing new to check.

If Compressor Status = "Off" and Last Compressor Status = "On", then set Last Compressor Switch Off Time = Current Time and check Last Compressor On Interval.

Calculate the Last Compressor On Interval using

Last Compressor On Interval = Last Compressor Switch Off Time - Last Compressor Switch On Time

If Last Compressor On Interval >= Minimum Compressor On Time, then Compressor On Cycle OK/not = "OK."

If Last Compressor On Interval < Minimum Compressor On Time, then Compressor On Cycle OK/not = "not OK." The compressor is not staying on long enough during cycling. Possible causes include an incorrectly specified minimum on time in the control algorithm or for compressors with minimum on/off times controlled by a relay a failed relay or one requiring adjustment.

Update Last Compressor Status : Set Last Compressor Status = Compressor Status\*

\*This over-writes previous compressor status with current status and should not be performed if previous status is required in subsequent processing.

Battelle Northwest, 2003

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.5.0 Diagnose Interlocks

![](images/5378caf3c75071201dd90411084280ab96afac36d840d1a15fb2f2e5dbd14771.jpg)  
Page 56

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.5.1.1 Verify Proper Condenser Pumps/Compressor Interlock

![](images/772c9bc6b0c81b5d4c8e1aa74e04602b1666ebf50de689b9bee5d8fb3a284c82.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.5.1.1.1 Evaluate Condenser Pumps Power vs Compressor Power

If Chiller Condenser Type = Air-Cooled, then terminate this analysis.

If Chiller Condenser Type = Water-cooled, then

compare the compressor status and condenser-pumps status for the current time.

If the Compressor Status = "On" and the Condenser-Pumps Status = "On," then Compressor Interlock With Condenser Pumps ${ \mathsf { O K } } / { \mathsf { n o t } } = " { \mathsf { O K } } "$

If the Compressor Status = "Off" and the Condenser-Pumps Status = "Off," then Compressor Interlock With Condenser Pumps ${ \mathsf { O K } } / { \mathsf { n o t } } = " { \mathsf { O K } } , "$ unless

the Compressor Status = "Off" and Last Compressor Status = "Off," and current Condenser Pumps Status = "Off" and Last Condenser Pumps Status = "On", then the condenser pumps are cycling (turning on and off) unnecessarily and Compressor Interlock With Condenser Pumps OK/not = "Not OK. Repeated frequent cycling will shorten the life of the condenser pumps."

If the Compressor Status = "On" and the Condenser-Pumps Status = "Off," then Compressor Interlock With Condenser Pumps OK/not = "not OK." The chiller cannot reject heat and this could result in damage to the compressor.

If the Compressor Status = "Off" and the Condenser-Pumps Status = "On," then further evaluation is required

If Current Time - Condenser Pumps Last Time Turned On <= Condenser Pumps Max Start-Up Time,then Compressor Interlock With Condenser Pumps OK/not = "OK" (for now; actually this corresponds to no fault detected).

If Current Time - Condenser Pumps Last Time Turned On > CondenserPumps Max Start-Up Time, then Compressor Interlock With Condenser Pumps OK/not = "Not OK." The condenser pumps are turning on too much in advance of the chiller and wasting energy.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

# 1.5.1.1.2 Update Last Compressor and Pumps Status

If Condenser Pumps Status = "On" and Last Condenser Pumps Status = "Off", then set Condenser Pumps Last Time Turned On = Current Time.

Otherwise, do not change Condenser Pumps Last Time Turned On, i.e., set Condenser Pumps Last Time Turned On = Condenser Pumps Last Time Turned On.

Then,

Set Last Compressor Status = Compressor Status.\*

Set Last Condenser-Pumps Status = Condenser-Pumps Status.\*

\*These actions over-write the previous statuses and should not be performed if the previous statuses are required in subsequent processing.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.5.1.2.1 Evaluate Condenser Fans Power vs Compressor Power

If Chiller Condenser Type = Water-Cooled, terminate this analysis.

If Chiller Condenser Type = Air-cooled, then

Compare the compressor status and condenser-fan status for the current time.

If the Compressor Status = "On" and the Condenser-Fans Status = "On," then Compressor Interlock With Condenser Fans OK/not = "OK"

If the Compressor Status = "Off" and the Condenser-Fans Status = "Off," then Compressor Interlock With Condenser Fans OK/not = "OK."

If the Compressor Status = "On" and the Condenser-Fans Status = "Off," then Compressor Interlock With Condenser Fans OK/not = "Not OK." The chiller cannot reject heat and this could result in damage to the compressor.

If the Compressor Status = "Off" and the Condenser-Fans Status = "On," then Compressor Interlock With Condenser Fans OK/not = "Not OK." The fans are running unnecessarily and wasting energy.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

1.5.1.3 Verify Proper CHW Pumps/ Compressor Interlock

![](images/62d20a76de3a606084deb7e176fb8aeb95bdef52d929532da560aa3ce69b496b.jpg)

Automated Diagnostics Version: 1.1   
Software Requirements Specification Date: 8/28/2003   
Software Requirements Specification 1-1.DOC 8/29/2003

## 1.5.1.3.1 Evaluate Chilled Water Pumps Power vs. Compressor Power

Compare the chiller status and chilled water pumps status for the current time.   
If the Compressor Status = "On" and the CHW Pumps Status = "On," then Compressor Interlock With   
CHW Pumps OK/not = "OK"   
If the Compressor Status = "Off" and the CHW Pumps Status = "Off," then Compressor Interlock With   
CHW Pumps OK/not = "OK," unless   
the Compressor Status= "Off" and Last Compressor Status = "Off," and current CHW Pumps Statu   
= "Off" and Last CHW Pumps Status = "On", then the condenser pumps are cycling (turning on   
and off) unnecessarily and Compressor Interlock With CHW Pumps OK/not = "Not OK."   
Repeated frequent cycling will shorten the life of the CHW Pumps.   
If the Compressor Status = "On" and the CHW-Pumps Status = "Off," then Compressor Interlock With   
CHW Pumps OK/not = "not OK." The chiller is operating without a load. Energy is being wasted and   
damage to the chiller may result.   
If the Compressor Status = "Off" and the CHW-Pumps Status = "On," then further evaluation is   
required.   
If Water-Side Economzing = "Yes", then Compressor Interlock With Condenser Pumps OK/not =   
"OK" (as far as we can tell).   
If Water-Side Economzing = "No", and   
If Current Time - CHW Pumps Last Time Turned On <= CHW Pumps Max Start-Up   
Time, then Compressor Interlock With CHW Pumps OK/not = "OK" (for now; actually   
this corresponds to no fault detected).   
If Current Time - CHW Pumps Last Time Turned On > CHW Pumps Max Start-Up   
Time, then Compressor Interlock With CHW Pumps OK/not = "Not OK." The CHW   
pumps are turning on too much in advance of the chiller and wasting energy.

Note: Applies to both water-cooled and air-cooled chillers.

Ref. File: 5.3.2 CHW Pumps interlock.doc

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

# 1.5.1.3.2 Update Last Compressor and CHW Pumps Status

If CHW Pumps $\mathsf { S t a t u s } = \ " \mathrm { O n } ^ { \prime \prime }$ and Last CHW Pumps Status = "Off", then set CHW Pumps Last Time Turned On = Current Time.

Otherwise, do not change CHW Pumps Last Time Turned On, i.e., set CHW Pumps Last Time Turned On = CHW Pumps Last Time Turned On.

Then,

set Last Compressor Status = Compressor Status.\*

and

set Last CHW Pumps Status = CHW Pumps Status.

\*This overwrites the previous status and should not be performed if subsequent processing requires the previous status.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.5.2 Diagnose CHW Interlocks

![](images/06c0c9eb7f78a6db249c2d282c6e5f5dd69b897b28d9abc212f8f259e86cf404.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

1.5.2.1 Verify Supply Fans/CHW Pumps Interlock

![](images/ad154fe3fbbdb8ba6ab8d90579b2836757de8555d82549e97f902904030e8506.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.5.2.1.1 Evaluate Supply Fans Current (or Power) vs Primary CHW Pumps Current (or Power)

For each set of primary CHW Pumps, Compare the CHW Pumps Collective Status and Supply Fan Status for the supply fans for each air handler served by this set of specific CHW Pumps.

If the CHW Pumps Collective $\mathsf { S t a t u s } = \ " \mathrm { O n } ^ { \prime \prime }$ and the Supply Fan $\mathsf { S t a t u s } = \ " \mathrm { O n } ^ { \prime \prime }$ for at least one of the air handlers served by this CHW Pumps, then set the Supply Fans/CHW Pumps Interlock OK/not for this set of CHW $\mathsf { P u m p s } = \mathsf {" O K } . ^ { \prime }$

If the CHW Pumps Collective $\mathsf { S t a t u s } = \ " \mathrm { O f f } ^ { \prime \prime }$ and the Supply Fan $\mathsf { S t a t u s } = \ " \mathrm { O f f } ^ { \prime }$ for all of the air handlers served by this set of CHW Pumps, then set the Supply Fans/CHW Pumps Interlock OK/not for this CHW $\mathsf { P u m p s } \mathsf { = } ^ { \mathsf { i n } } \mathsf { O K . } ^ { \mathsf { - } }$

If the CHW Pumps Collective $\mathsf { S t a t u s } = \ " \mathrm { O f f } ^ { \prime }$ and the Supply Fan $\mathsf { S t a t u s } = \ " \mathrm { O n } ^ { \prime \prime }$ for at least one of the air handlers served by this set of CHW Pumps, then set the Supply Fans/CHW Pumps Interlock OK/not for this set of CHW Pumps = "Possible problem with supply fan control--check to see if loads in the spaces served are being met for supply fans with Supply Fans $\mathsf { S t a t u s } = \ " \mathrm { O n } ^ { \prime \prime }$ that are part of air handlers served by these CHW Pumps. Occupant complaints about temperature or stuffiness may be in indicator of the load not being met.

If the CHW Pumps Collective $\mathsf { S t a t u s } = \ " \mathrm { O n } ^ { \prime \prime }$ and the Supply Fan $\mathsf { S t a t u s } = \ " \mathrm { O f f } ^ { \prime \prime }$ for all of the air handlers served by this set of CHW Pumps, then set the Supply Fans/CHW Pumps Interlock OK/not for this CHW Pumps = "Not OK." These CHW Pumps is operating unnecessarily and is wasting energy. The CHW Pumps should not operate unless at least one of the supply fans in an air handler served by these CHW Pumps is on.

Notes: This diagnostic can be applied to current (or power) measured for each supply fan individually or to the collective current for all supply fans served by a CHW pump together.

Equipment status is determined in Process 7.0.

Ref. File: 5.8 supply fan-CHW pump interlock.doc

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

1.5.2.2 Verify Supply Fans/ Secondary Pumps Interlock

![](images/3783c1f799d57c18bb5f2714f20e1f49f690d91ad81d61af35ed34b6c7fb4864.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

# 1.5.2.2.1 Evaluate Supply Fans Current (or Power) vs Secondary CHW pumps Current (or Power)

For chilled-water distirbution systems with secondary CHW pumps.

For each secondary set of CHW pumps,

compare the Secondary CHW pumps Collective Status and Supply Fans Status for the supply fans for each air handler served by this specific secondary CHW pump.

If the Secondary CHW pumps Collective Status = "On" and the Supply Fans Status = "On" for at least one of the air handlers served by this set of secondary CHW pumps, then set the Supply Fans/Secondary CHW Pumps Interlock OK/not for this set of secondary CHW pumps = "OK."

If the Secondary CHW pumps Collective Status = "Off" and the Supply Fans Status = "Off" for all of the air handlers served by this set of secondary CHW pumps, then set the Supply Fans/Secondary CHW Pumps Interlock OK/not for this set of secondary CHW pumps = "OK."

If the Secondary CHW pumps Collective Status = "Off" and the Supply Fans Status = "On" for at least one of the air handlers served by this set of Secondary CHW pumps, then set the Supply Fans/Seondary CHW Pumps Interlock OK/not for this set of secondary CHW pumps = "Possible problem with supply fan control--check to see if loads in the spaces served are being met" for supply fans with Supply Fans Status = "On" that are part of air handlers served by this set of secondary CHW Pumps.

If the Secondary CHW pumps Collective Status = "On" and the Supply Fans Status = "Off" for all of the air handlers served by this set of Secondary CHW pumps, then set the Supply Fans/Secondary CHW Pumps interlock OK/not for this set of secondary CHW pump = "Not OK." This set of secondary CHW pumps is operating unnecessarily and is wasting energy. The set of secondary CHW pumps should not operate unless at least one of the supply fans in an air handler served by this set of secondary CHW pumps is on.

Notes: This diagnostic can be applied to current (or power) measured for each supply fan individually or to the collective current for all supply fans served by a set of secondary CHW pump togethers.

Equipment status is determined in Process 7.0.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

1.5.2.3 Verify Secondary/Primary CHW Pumps Interlock

![](images/16eb7e6bc24515178858b72249695ae0e183ab2d698819a2351e79d7342751c6.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.5.2.3.1 Evaluate Secondary CHW pumps Current (or Power) vs Primary CHW Pumps Current (or Power)

For each set of primary CHW pumps,

For each set of secondary CHW pumps served by the selected set of primary CHW Pumps,

Compare the primary CHW Pumps Collective Status and Secondary CHW pumps Collective Status for each set of secondary CHW pump served by this specific set of primary CHW Pumps.

If the primary CHW pumps Collective Status = "On" and the Secondary CHW pump Status = "On" for at least one of the secondary CHW pumps served by this set of primary CHW pumps, then set Secondary/Primary CHW Pumps Interlock OK/not for this set of primary CHW pump = "OK."

If the primary CHW pumps Collective Status = "Off" and the Secondary CHW pump Status = "Off" for all of the secondary CHW pumps served by this set of primary CHW pumps, then set Secondary/Primary CHW Pumps Interlock OK/not for this set of primary CHW pumps = "OK."

If the primary CHW pumps Collective Status = "Off" and the Secondary CHW pump Status = "On" for at least one of the secondary CHW pumps served by this set of primary CHW pumps, then set Secondary/Primary CHW Pumps Interlock OK/not for this set of primary CHW pumps = "Not OK." The secondary CHW pumps that are one are wasting energy. Secondary CHW pumps should only operate when the set of primary CHW pumps is operating.

If the primary CHW Pumps Collective Status = "On" and the Secondary CHW pump Status = "Off" for all of the secondary CHW pumps served by this set of primary CHW pumps, then set Secondary/Primary CHW Pumps Interlock OK/not for this set of primary CHW pumps = "Not OK." This set of primary CHW pumps is operating unnecessarily and is wasting energy. The set of primary CHW pump should not operate unless at least one of the secondary CHW pumps served by this set of primary CHW pumps is on.

Notes: This diagnostic can be applied to current (or power) measured for each secondary CHW pump individually or to the collective current for all secondary CHW pumps served by a CHW pump together.

Equipment status is determined in Process 7.0.

Ref. File: 5.9 secondary CHWP interlock.doc

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 1.6.0 Diagnose Chiller Performance

Placeholder only for Round 2.

Chiller Performance is a candidate for development of diagnostics for Round 2.

Enforma help suggests 4 plots that may be useful for Chiller Performance Diagnostics:

¸ Compressor Power vs. Ambient Temperature

¸ Compressor Power vs. Condenser Inlet Temperature (cooling tower outlet temperature)

¸ Compressor Power vs. Chiller Delta T

¸ Compressor Power vs. Chiller Inelt Temperature

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.0 Diagnose Cooling Tower

![](images/a72079cbbae02fe4fae52630f2ccacd677f0ae785ef4504db11e71ae4960afa3.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

2.1 Diagnose Cooling Tower Interlocks

![](images/f7572a0438bd97a6023ec2df1170433e4bfb0c745cc3b4d0b234639a35b7e08a.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.1.1 Evaluate CT Fans Status vs. Condenser Pumps Status

Compare the CT Fans Status and Condenser Pumps Status for the current time.

If the CT Fans $\mathsf { S t a t u s } = \ " \mathrm { O n } ^ { \prime \prime }$ and the Condenser Pumps $\mathsf { S t a t u s } = \ " \mathrm { O n } , \ "$ then CT Fans/Condenser Pumps Interlock ${ \mathsf { O K } } / { \mathsf { N o t } } = " { \mathsf { O K } } "$

If the CT Fans $\mathsf { S t a t u s } = \ " \mathrm { O f f } ^ { \prime \prime }$ and the Condenser Pumps $\mathsf { S t a t u s } = \ " { \mathrm { o f f } } , \ "$ then CT Fans/Condenser Pumps Interlock ${ \mathsf { O K } } / { \mathsf { N o t } } = " { \mathsf { O K } } . ^ { \prime }$

If the CT Fans $\mathsf { S t a t u s } = \ " \mathrm { O n } ^ { \prime \prime }$ and the Condenser Pumps $\mathsf { S t a t u s } = \ " { \mathrm { o f f } } , \ "$ then CT Fans/Condenser Pumps Interlock ${ \mathsf { O K } } / { \mathsf { N o t } } = " { \mathsf { N o t } } { \mathsf { O K } } . "$ The CT Fans must be off when the condenser pumps are off, otherwise energy is being wasted.

If the CT Fans $\mathsf { S t a t u s } = \ " \mathrm { O f f } ^ { \prime \prime }$ and the Condenser Pumps $\mathsf { S t a t u s } = \ " { \mathsf { O n } } , \mathsf { \Omega } ,$ then CT Fans/Condenser Pumps Interlock ${ \mathsf { O K } } / { \mathsf { N o t } } = " { \mathsf { O K } } . "$ The cooling tower Fans may be off when the condenser pumps are running, but this should not always be the case.

Note: This process uses as inputs the CT Fans Status and the Condenser Pumps Status that are determined in Process 7.0.

Values of CT Fans/Condenser Pumps Interlock ${ \mathsf { O K } } / { \mathsf { N o t } } = " { \mathsf { O K } } "$ should be interpretted more precisely as "no problem has been detected with this interlock." It is possible that no problem is detected under current conditions,yet an interlock problem exists. This is particularly true when CT Fans $\mathsf { S t a t u s } = \ " \mathrm { O f f } ^ { \prime }$ and Condenser Pumps $\mathsf { S t a i u s } = " \mathsf { O n } , "$ which while OK under some condtions is not always OK. Additional diagnostics would be useful here.

Ref. File: 1.22 Evaluate Plot of CT Fan vs. $\mathsf { C C P }$

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

2.2 Diagnose Cooling Tower Temperature Control/Cycling  
![](images/2f4c287abd13ef694cd58f93eee60c0a238ebe66071f1b3b4d5291965ea48c6d.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.2.1 Diagnose Sump Temperature Control

![](images/fb57215f35477cbd3d12fbb431e8103c39aa50bf4e122bc410d3274f0bcd7da5.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

# 2.2.1.1 Filter CT Sump Temp and Ambient wb Temp for Times When Condenser Pumps are On

For each triplet of (Condenser Pumps Status, CT Sump Temperature, and Ambient wb Temperature)

reject (i.e., filter out) those triplets for which Condenser Pumps Status = off.   
pass those triplets for which Condenser Pumps status = on.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

# 2.2.1.2 Evaluate Filtered CT Sump Temp vs. Filtered Ambient wb Temp

Determine if CT fans are on when Sump Temp is above its on setpoint   
If Sump Temperature > CT Fans On Setpoint and CT Fans Status = "On,"   
then set Sump Temp Control OK/Not= "OK"   
If Sump Temperature > CT Fans On Setpoint and CT Fans Status = "Off,"   
then set Sump Temp Control OK/Not= "Not OK. The CT fans are off but should be on."   
Possible causes include:   
control problem   
sump temperature sensor problem   
electrical problem (motor failure)   
other problems with the fan motor   
Determine if CT fans are off when sump Temp is below the off setpoint   
If Sump Temperature <= CT Fans Off Setpoint and CT Fans Status = "On,"   
then set Sump Temp Control OK/Not= "Not OK. The CT fans are on but should be off."   
Possible causes include:   
control problem   
actuator or relay problem   
If Sump Temperature <= CT Fans Off Setpoint and CT Fans Status = "Off,"   
then set Sump Temp Control OK/Not= "OK."  
Ref. File: 2.1.1 Sump Temperature Control Diagnostics

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.2.2 Diagnose Cooling Tower Cycling

![](images/8e436e45a1a5b7d1459031a5b87a348c0f46ffadee0f01c9027be1162f794669.jpg)

Possible causes include::   
The timer that is supposed to eliminate short cycling is not working properly.   
The "on" and "off" control setpoints for the fans are too close to one another.   
Possible corrective actions include:   
Check the control algorithm for the fans if it is controlled by software. Increase the minimum off time in the   
software, as necessary, to meet the manufacturers specification for minimum off time.   
Check the performance of the time-delay relay. Energize the relay and manually time the delay until action.   
Compare the measured time with the specification. Replace or adjust the relay if it is out of spec.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.2.2.1 Evaluate CT Fans Cycling Times

Determine if new cycling information is available to analyze (fans currently on).

If CT Fans Status = "On" and Last CT Fans Status = "On," then terminate this evaluation. There is nothing new to check.

If CT Fans Status = "On" and Last CT Fans Status = "Off," then set Last CT Fans On Time = Current Time and check Last CT Fans Off Interval.

If Last CT Fans Off Interval >= Minimum CT Fans Off Time, then CT Cycling OK/Not = "OK."

If Last CT Fans Off Interval < Minimum CT Fans Off Time, then CT Cycling OK/Not = "Not OK." The CT fans are not staying off long enough during cycling.

Determine if new cycling information is available to analyze (fans currently off).

If CT Fans Status = "Off" and Last CT Fans Status = "Off," then terminate this evaluation. There is nothing new to check.

If CT Fans Status = "Off" and the Last CT Fans Status = "On," then set Last CT Fans Off Time = Current Time and check Last Fan On Interval.

If Last CT Fans On Interval >= Minimum CT Fans On Time, then CT Cycling OK/Not = "OK."

If Last CT Fans On Interval < Minimum CT Fans On Time, then CT Cycling OK/Not = "Not OK." The CT fans are not staying on long enough during cycling.

Possible causes include:

The timer that is supposed to eliminate short cycling is not working properly.

The "on" and "off" control setpoints for the fans are too close to one another.

The cooling tower capacity is too great for the load, so the fans rapidly cycle off (i.e., the on time is very short) because the load is met quickly.

Check the control algorithm for the fans if it is controlled by software. Increase the minimum off time in the software, as necessary, to meet the manufacturers specification for minimum off time.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.2.3 Diagnose CT Based on Approach

![](images/e5500d8d052ea47cfb63a9c82d358118da1db87479ff2a688c278f55e94ac698.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.2.3.1 Evaluate Filtered CT Approach vs. Filtered Ambient wb Temp

![](images/2feba36bda27daac56eddebe9056b1c61aadbca0c78fd9f6045d3e9fc92e5eb8.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

# 2.2.3.1.1 Filter CT Approach and Ambient wb Temp for Condensor Pumps "On"

For each triplet of (Condenser Pumps Status, CT Approach, and Ambient wb Temperature)

reject (i.e., filter out) those triplets for which Condenser Pumps Status = off.   
pass those triplets for which Condenser Pumps Status = on.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

2.2.3.1.2 Evaluate CT Approach Behavior

![](images/eb09d494543c3e6d5f2fb0c306a17b3e91ecb45c66798fce059306a15643ce52.jpg)  
Page 84

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.2.3.1.2.1 Filter for Fans "On" and Sump Temp Setpoint

For each point on the Plot of filtered CT Approach vs. Filtered Ambient wb Temp, reject it

if the CT Fans Status is "off" or

if the Sump Temperature < CT Fans "on" setpoint

otherwise, accept it (pass it).

Ref: 2.4 approach diagnostics discussion.doc

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.2.3.1.2.2 Check Approach

Compare values of CT Approach to the CT Approach Benchmark.

If CT Approach is <= CT Approach Benchmark, then set CT Approach ${ \mathsf { O K } } / { \mathsf { N o t } } = " { \mathsf { O K } } "$

If CT Approach is > CT Approach Benchmark, then there is a problem (not OK) with CT heat rejection. Set CT Approach $\mathsf { O K / N o t } = \mathsf {" N o t } \mathsf { O K } .$ There is a problem with heat rejection from the cooling tower."

Possible causes of heat rejection degradation (i.e., CT Approach $\mathsf { O K } / \mathsf { N o t } = \mathsf { N o t } \mathsf { O K } ) \mathrm { : }$

Cooling tower media fouled due to mineral deposits or ambient dirt/dust/etc. Need to inpsect. Restricted airflow for other reasons (e.g., piece of cardboard stuck over part of cooling tower air inlet)

Condenser pump fouling, pipe fouling, or other restrictions on the water side.

Ref. File: 2.4 Approach diagnostics discussion.doc

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.2.3.1.3 Determine Benchmark CT Approach

CT Approach Benchmark is a user input (in the current process; see note below).

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.2.3.2 Calculate CT Approach

For each pair of values of Sump Temperature and Ambient wb Temperature corresponding to the same time, calculate the CT Approach using

CT Approach = Sump Temp - Ambient Wet Bulb Temp

Note: Approach is not "controlled" - it is the difference between the sump temperature, which IS controlled, and the ambient wb temperature, which is NOT controlled.

Ref: 2.4 approach diagnostics.doc

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.3 Diagnose Cooling Tower Capacity

![](images/e26a56eb3265c77ade2c57742b7bd08a53e882ed9aa6607fdb3ec3787dfd3f22.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.3.1 Diagnose CT Fans Staging

![](images/6e6bb445a0342164579c3d573788b10b9ca69c9dce3863922a38aea4be1983bf.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.3.1.1 Filter CT Fans Current and Sump Temp for CT Pumps "On"

For each triplet of (Condenser Pumps Status, CT Fans Status, and CT Sump Temperature) reject (i.e., filter out) those triplets for which Condenser Pumps Status = off. pass those triplets for which Condenser Pumps status = on.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

# 2.3.1.2 Evaluate Filtered CT Fans Current (or Power) vs. Filtered Sump Temp Plot

Compare Sump Temperature to the CT Fans "On" Setpoint (maximum Sump Temperature Setpoint). If Tsump < CT Fans "On" Setpoint, then set Fans Staging OK/Not = "OK (as far as we can tell)" If Tsump > CT Fans "On" Setpoint, and CT Fans Status = "On" for all CT fans, then set Fans Staging OK/Not = "OK."

If Tsump > CT Fans "On" Setpoint and CT Fans Status ¹ "On" for all CT fans (i.e., all CT fans are not on), set Fans Staging OK/Not = "not OK. There is a fan staging problem and the cooling tower is not maintaining the Sump Temp as low as it could/should."

Compare Tsump to the CT Fans "Off" Setpoint (minimum Sump Temperature Setpoint).   
If Tsump > CT Fans "Off" Setpoint, then set Fans Staging OK/Not = "OK (as far as we can tell)."   
If Tsump < CT Fans "Off" Setpoint, and if CT Fans Status = "Off" for all CT Fans (i.e., all CT fans are off), then   
set Fans Staging OK/Not = "OK."   
If Tsump < CT Fans "Off" Setpoint, and If any CT Fans Status = "On" (i.e., any CT fan is "on"), then set Fans   
Staging OK/Not = "Not OK. There is a fan staging problem and energy is being wasted. All CT Fans   
should be off."

## Note:

The minimum and maximum sump temp setpoints are currently specified as inputs. A procedure could be developed to derive them from performance data. This would reduce the number of user inputs required.

Note: A process for checking the individual fan stages has not been specified here. it would need to be added. See Behavior 3 in the reference file.

Tsump = Sump Temp

Tsump maximum setpoint = maximum Sump Temperature setpoint

Tsump minimum setpoint = minimum Sump Temperature setpoint

Ref. File: 3.3 fan staging diagnostic.doc

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

![](images/b5237de4d2eaebaf877e3ebd9f17a5f92530dbfec9f4efdf103c2e60c73059b1.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.3.2.1 Filter CT Range and Ambient wb

![](images/bd9e4ba616485f7c00ee2f626dd21d7ce35b48da728e229b1b4b4929bb0861e8.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.3.2.1.1 Filter CT Range and Ambient wb Temp for Condenser Pumps "On"

For each triplet of (Condenser Pumps Status, CT Range, and Ambient wb Temperature) reject (i.e., filter out) those triplets for which Condenser Pumps Status = off. pass those triplets for which Condenser Pumps status = on.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.3.2.1.2 Filter for Fans "On" and Sump-Temp Setpoint

For each point on the Plot of filtered CT Range vs. Filtered Ambient wb Temp, reject it

if the Fans Status is "off" or

if the Sump Temperature is below the CT Fans "On" Setpoint (Maximum Sump Temperature Setpoint).

otherwise, accept it (pass it).

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.3.2.2 Evaluate CT Range Behavior

![](images/67e30491f1f8dd97b5e1dda4ad9f3e7240be7b368e67cfa0a9fd3c6661ae24cd.jpg)  
Ref. File: 3.2.3 Range diagnostics discussion.doc

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 2.3.2.3 Calculate CT Range

For each time increment (and pair of necessary temperature values), calculate the CT Range, using the formula

CT Range = CT Sump Temperature - CT Inlet Temperature.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

![](images/dfce8adb0d419dde8e982223a9e37f2a2d5b421254b3c92d44aba8bb434eb742.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.1 Determine Compressor Status and State

![](images/a3ec4c9173f8a9d3d347a8b0887dfbfa7da695f0b46517824db8d7721846d4bf.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.1.1 Set Compressor "On" Threshold

Calculate the Compressor "On" Threshold using

Compressor "On" Threshold = Compressor P x Compressor Motor Rated Current (or Power)

## Notes:

The chiller is "on" when the compressor is "on;" therefore, the chiller status can be determined by evaluating the compressor on/off status. As the result, the Chiller "On" Threshold is set by setting the Compressor "On" threshold.

The Compressor "On" Threshold is calculated from input power rating of the compressor motor.

Compressor P has values that range from 10 to 50% -- this can be a user input.

Ref file: 2.1CHW temperature control.doc

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.1.2 Assess Compressor Status and State

For each value of Compressor Current (or Power),   
compare Compressor Current (or Power) to the Compressor "On" Threshold.   
If the value of Compressor Current (or Power) <= Compressor "On" Threshold, then set Compressor   
Status = "Off" and set Compressor State = "Off"   
If the value of Compressor Current (or Power) > Compressor "On" Threshold, then set Compressor   
Status = "on."   
If Compressor Status = "On", then evaluate Compressor State as follows:   
Update the value of Last Compressor State, using   
Last Compressor State = Compressor State.   
Determine and assign the new value of Compressor State for the current time   
Check if the compressor is already in steady state   
If Last Compressor State = Steady,   
then set Compressor State = "Steady"   
If Compressor Status = "On" and the Last Compressor State = "Transient", then   
Calculate Drop in CHW Supply Temperature using   
Drop in CHWST = CHWST Last - CHWST   
Compare Drop in CHW Supply Temperature to the Minimum Transient Decrease in CHWST.   
If Drop in CHWST > Minimum Transient Decrease in CHWST, then set Compressor   
State = "Transient".   
If Drop in CHWST <= Minimum Transient Decrease in CHWST, then set Compressor   
State = "Steady"   
Update CHWST Last   
CHWST Last = CHWST

Note: Compressor Status = Chiller Status

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.1.3 Calculate the Minimum Transient Decrease in CHWST

Calculate the Minimum Transient Decrease in CHWST using the relation:

Minimum Transient Decrease in CHWST = CHW Transient Decrease Factor \* (CHWST at Last Time Off - CHWST Setpoint)

Set new value of CHWST at Last Time Off,

If Compressor Status = "Off" and Last Compressor Status = "Off", then set CHWST at Last Time Off = CHWST

If Compressor Status = "On" and Last Compressor Status = "Off", then set CHWST at Last Time Off = CHWST Last

If Compressor Status = "On" and Last Compressor Status = "On" then set CHWST at Last Time Off = CHWST at Last Off Time (i.e., not change).

Update Last Compressor Status

Last Compressor Status = Compressor Status\*

\*This over-writes the previous compressor status with the current status and should not be performed if the previous status is required in subsequent processing.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.2 Determine Condenser Pumps Status

![](images/8dea9d653bf2b7f91e50117bb0a4195720583e1db3cb896a2bc2d6565f850cee.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.2.1 Set Condenser Pumps"On" Threshold"

Calculate the Condenser Pumps "On" Threshold using

Condenser Pumps "On" Threshold = Condenser Pumps P x Condenser Pump Motors Rated Current (or Power)

Notes:

Condenser Pumps P has values that range from 10 to 50% -- this can be a user input.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.2.2 Assess Condenser Pumps Status

For each value of Condenser Pumps Current (or Power),

compare Condenser Pumps Current (or Power) to the Condenser Pumps "On" Threshold.

If the value of Condenser Pumps Current (or Power) <= Condenser Pumps "On" Threshold, then set Condenser Pumps Status = "Off."

If the value of Condenser Pumps Current (or Power) > Condenser Pumps "On" Threshold, then set Condenser Pumps Status = "On."

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.3 Determine CHW Pumps Status

![](images/5629f1db6002d0b9b47cd2ac2fe5119d2e3fd055029acc966ef39ce40a50663a.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.3.1 Set CHW Pumps "On" Threshold"

Calculate the CHW Pumps "On" Threshold using

CHW Pumps "On" Threshold = CHW Pumps P x CHW Pumps Motor Rated Current (or Power)

Notes:

CHW Pumps P has values that range from 10 to 50% -- this can be a user input.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.3.2 Assess CHW Pumps Status

For each value of CHW Pumps Current (or Power),   
compare CHW Pumps Current (or Power) to the CHW Pumps "On" Threshold.   
If the value of CHW Pumps Current (or Power) <= CHW Pumps "On" Threshold, then set   
CHW Pumps Status = "off."   
If the value of CHW Pumps Current (or Power) > CHW Pumps "On" Threshold, then set CHW   
Pumps Status = "On."

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.4 Determine Secondary CHW Pumps Status

![](images/7fdc58c3e786075255fecc1ef7d8e8f86fec185cd5fac157d35071c17ac000a9.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

# 3.4.1 Set Secondary CHW Pumps "On" Threshold"

Calculate the Secondary CHW Pumps "On" Threshold using

Secondary CHW Pumps "On" Threshold = Secondary CHW Pumps P x Secondary CHW Pumps Motors Rated Current (or Power)

Notes:

Secondary CHW Pumps P has values that range from 10 to 50% -- this can be a user input.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.4.2 Assess Secondary CHW Pumps Status

For each value of Secondary CHW Pumps Current (or Power),

compare Secondary CHW Pumps Current (or Power) to the Secondary CHW Pumps "On" Threshold. If the value of Secondary CHW Pumps Current (or Power) <= Secondary CHW Pumps "On" Threshold, then set Secondary CHW Pumps Status = "off."

If the value of Secondary CHW Pumps Current (or Power) > Secondary CHW Pumps "On" Threshold, then set Secondary CHW Pumps Status = "On."

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.5 Determine CT Fans Status

![](images/b3cc052e262616146bc9b6ac6dcf20aef76d11cafa08e805a0d331338324dc52.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.5.1 Set CT Fans "On" Threshold

Calculate the CT Fans "On" Threshold using

CT Fans "On" Threshold = CT Fans P x CT Fan Motors Rated Current (or Power)

Notes:

CT Fans P has values that range from 10 to 50% -- this can be a user input.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.5.2 Assess CT Fans Status

For each value of CT Fans Current (or Power),   
compare CT Fans Current (or Power) to the CT Fans "On" Threshold.   
If the value of CT Fans Current (or Power) <= CT Fans "On" Threshold, then set CT Fans Status   
= "Off."   
If the value of CT Fans Current (or Power) > CT Fans "On" Threshold, then set CT Fans Status   
= "On."

Note:

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.6 Determine Condenser Fans Status

![](images/c6b734ef614ca59c6bce2779fd5d1e5c5e15c89fbdf4fecb3af149112ea63653.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.6.1 Set Condenser Fans "On" Threshold

Calculate the Condenser Fans "On" Threshold using

Condenser Fans "On" Threshold = Condenser Fans P x Condenser Fan Motors Rated Current (or Power)

Notes:

Condenser Fans P has values that range from 10 to 50% -- this can be a user input.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.6.2 Assess Condenser Fans Status

For each value of Condenser Fans Current (or Power),   
compare Condenser Fans Current (or Power) to the Condenser Fans "On" Threshold.   
If the value of Condenser Fans Current (or Power) <= Condenser Fans "On" Threshold, then set   
Condenser Fans Status = "Off."

If the value of Condenser Fans Current (or Power) > Condenser Fans "On" Threshold, then set   
Condenser Fans Status = "On."

Note:

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.7 Determine Supply Fans Status

![](images/bcc53a1677e629823649ad0a98caefe6f4d691ff060117eaedfb598ff34a4dc7.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.7.1 Set Supply Fans "On" Threshold

Calculate the Supply Fans "On" Threshold using

Supply Fans "On" Threshold = Supply Fans P x Supply Fan Motors Rated Current (or Power)

Notes:

Supply Fans P has values that range from 10 to 50% -- this can be a user input.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>Software Requirements Specification 1-1.DOC 8/29/2003</td></tr></table>

## 3.7.2 Assess Supply Fans Status

For each value of Supply Fans Current (or Power), compare Supply Fans Current (or Power) to the Supply Fans "On" Threshold. If the value of Supply Fans Current (or Power) <= Supply Fans "On" Threshold, then set Supply Fans $\mathsf { S t a t u s } = \ " { \mathrm { { \Omega } } } { \mathrm { { \Omega } } } { \mathrm { { \Omega } } } ^ { \prime }$

If the value of Supply Fans Current (or Power) > Supplyr Fans "On" Threshold, then set Supply Fans Status = "On."

Note:

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

5. Appendix B: Chiller, Cooling Tower, and Chilled-Water Distribution Data Dictionary

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Ambient wbTemperature</td><td rowspan=1 colspan=1>Ambient wet-bulb temperature of the outdoorair. Equivalent to the Outdoor-Air Wet-BulbTemperature and Outdoor-Air TemperatureWet-Bulb (OATWB)</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>Ambient Wet-BulbTemperature(OATWB)</td><td rowspan=1 colspan=1>Wet-bulb temperature of the outdoor air.Equivalent to Outdoor-Air Wet-BulbTemperature and Outdoor-Air TemperatureWet Bulb (OATWB)</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>Ambient-AirTemperature (OAT)</td><td rowspan=1 colspan=1>Equivalent to Outdoor-Air Temperature (OAT)and is the dry-bulb temperature of the ambientoutdoor air.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>Chiller &quot;On&quot;Threshold</td><td rowspan=1 colspan=1>The value of Chiller Current (or Chiller Power)above which the Chiller Status is considered&quot;On.&quot;</td><td rowspan=1 colspan=1>On.</td></tr><tr><td rowspan=1 colspan=1>Chiller CondenserType</td><td rowspan=1 colspan=1>The type of cooling for the chiller condenser. Ittakes values of “Water cooled” or “Air cooled”</td><td rowspan=1 colspan=1>Water cooled or air cooled.</td></tr><tr><td rowspan=1 colspan=1>Chiller On/off Status</td><td rowspan=1 colspan=1>An indicator of whether the chiller is on or off.Chiller on/off Status = Compressor on/offStatus.</td><td rowspan=1 colspan=1>On or off.</td></tr><tr><td rowspan=1 colspan=1>Chiller Schedule</td><td rowspan=1 colspan=1>Schedule of chiller on and off times during aday. The schedule may vary based on day ofweek, type of day (e.g., weekday vs. weekendvs. holiday), or time of year. The scheduledoes not take into account chiller cycling,which may be caused by changes in loadduring a scheduled &quot;on&quot; time period.</td><td rowspan=1 colspan=1>Absolute On/off times</td></tr><tr><td rowspan=1 colspan=1>Chiller ScheduleOk/not</td><td rowspan=1 colspan=1>Indicator of whether the chiller is operating onlyduring scheduled times or not.</td><td rowspan=1 colspan=1>Ok.Not Ok. The chiller isoperating outside itsscheduled time.</td></tr><tr><td rowspan=1 colspan=1>Chiller Status</td><td rowspan=1 colspan=1>Same as Chiller On/off Status. An indicator ofwhether the chiller is on or off. Takes values of&quot;on&quot; or &quot;off.&quot; Chiller status = Compressorstatus.</td><td rowspan=1 colspan=1>On or off.</td></tr><tr><td rowspan=1 colspan=1>Chiller System Type</td><td rowspan=1 colspan=1>The type of chiller system. Chiller System</td><td rowspan=1 colspan=1>Water cooled or air cooled.</td></tr><tr><td rowspan=1 colspan=1>Chiller/CompressorStart-Up Time</td><td rowspan=1 colspan=1>Estimated time over which the compressorcurrent/power spikes after the compressor isturned from off to on. This could be estimatedmanually and entered by the user or might bederived automatically from compressor data ina separate process (not yet specified in thismodel).</td><td rowspan=1 colspan=1>Time difference in minutes.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>CHWdDown</td><td rowspan=1 colspan=1>The maximum temperature increment belowthe CHW Setpoint which when subtracted fromthe CHW Setpoint results in the minimumacceptably-controlled CHW Temperature.</td><td rowspan=1 colspan=1>Temperature difference indegrees F.</td></tr><tr><td rowspan=1 colspan=1>CHWdUp</td><td rowspan=1 colspan=1>The maximum temperature increment abovethe CHW Setpoint which when added to theCHW Setpoint results in the maximumacceptably-controlled CHW Temperature</td><td rowspan=1 colspan=1>Temperature difference indegrees F.</td></tr><tr><td rowspan=1 colspan=1>CHW PumpsCollective Status</td><td rowspan=1 colspan=1>The status of all the primary chilled waterpumps in an associated set taken as a singleunit. If at least one pump of the set is ON, thecollective status is ON. If all the pumps in theset are OFF, the collective status is OFF.</td><td rowspan=1 colspan=1>On or Off.</td></tr><tr><td rowspan=1 colspan=1>CHW Pumps Current(or Power)</td><td rowspan=1 colspan=1>Chilled Water Pumps Current (or Power). Themeasured value of current (or power) for theprimary CHW pumps motor.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>CHW Pumps LastTime Turned On</td><td rowspan=1 colspan=1>Chilled Water Pumps Last Time Turned On.The time of the last measurement of CHWWater Pumps Status at which the CHW PumpsStatus was &quot;On&quot; while the Preceding CHWPumps Status was &quot;Off.&quot;</td><td rowspan=1 colspan=1>Absolute time in minutes.</td></tr><tr><td rowspan=1 colspan=1>CHW Pumps MaxStart-Up Time</td><td rowspan=1 colspan=1>Chilled Water Pumps Max Start-Up Time. Themaximum time that the CHW Pumps shouldturn on before the compressor turns on. Thiscan be set by default to 5 minutes.</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>CHW Pumps MotorRated Current (orPower)</td><td rowspan=1 colspan=1>Chilled Water Pumps Motor Rated Current (orPower). Current (or power) rating of theprimary CHW Pumps motor from the motornameplate.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>CHW Pumps P</td><td rowspan=1 colspan=1>Chilled Water Pumps P. Fraction of ChilledWater Pumps Motor Rated Current (or Power)selected for the &quot;On&quot; Threshold.</td><td rowspan=1 colspan=1>None.</td></tr><tr><td rowspan=1 colspan=1>CHW Set Point</td><td rowspan=1 colspan=1>Chilled Water Set Point. The set point for thechilled water supply temperature.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>CHWST</td><td rowspan=1 colspan=1>Chilled Water Supply Temperature.Temperature of the chilled water leaving thechiller and entering the chilled waterdistribution system at the current time</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>CHWST Alarm</td><td rowspan=1 colspan=1>A variable indicating the current value of thealarm for the chilled water supply temperaturedeviations from set point. It takes values of“Too High”, “Too Low”, and “OK”. It indicateswhether the CHW temperature is maintainedadequately over a designated minimumnumber of time steps (CHWST Alarm IntervalHigh and CHWST Alarm Interval Low).</td><td rowspan=1 colspan=1>Too high, too low or Ok.</td></tr><tr><td rowspan=1 colspan=1>CHWST AlarmEvaluation Interval</td><td rowspan=1 colspan=1>The number of time steps immediatelypreceding the current time over which thecriterion for a CHWST alarm is evaluated. Thisparameter takes integer values and isadjustable to change the low-alarm sensitivity.Its value may be specified as a set-up variable,default value, or empirically adjustable.</td><td rowspan=1 colspan=1>Number of time steps.</td></tr><tr><td rowspan=1 colspan=1>CHWST AlarmTrigger High</td><td rowspan=1 colspan=1>The minimum fraction of values of the variableCHWST Maintained OK/not that are equal to&quot;Too High&quot;, when evaluated over CHWSTAlarm Evaluation Interval time steps, for a highalarm to be reported, i.e., for CHWST Alarm tobe set equal to “CHWST High.&quot;This variabletakes values between 0.51 and 1.0 (i.e., 51%and 100%). It may be a user set-up input, adefault value, or a empirically adjustedsensitivity. The current process descriptionsassume that High and Low alarms cannotoccur simultaneously.</td><td rowspan=1 colspan=1>Real values between 0.51and 1.00.</td></tr><tr><td rowspan=1 colspan=1>CHWST AlarmTrigger Low</td><td rowspan=1 colspan=1>The minimum fraction of values of the variableCHWST Maintained OK/not that are equal to&quot;Too Low&quot;, when evaluated over CHWSTAlarm Evaluation Interval time steps for analarm to be reported, i.e., for CHWST Alarm tobe set equal to “CHWST Low.&quot;This variabletakes values between 0.51 and 1.0 (i.e., 51%and 100%). It may be a user set-up input, adefault value, or a empirically adjustedsensitivity.</td><td rowspan=1 colspan=1>Real values between 0.51and 1.00.</td></tr><tr><td rowspan=1 colspan=1>CHWST at Last TimeOff</td><td rowspan=1 colspan=1>Chilled Water Supply Temperature measuredthe last time the compressor was off.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>CHWST Deviation(Chilled WaterSupply TemperatureDeviation)</td><td rowspan=1 colspan=1>CHWST Deviation = CHW Temperature - CHWSetpoint. The amount by which the actualChilled Water Supply Temperature deviatesfrom the chilled water set point at the presenttime.</td><td rowspan=1 colspan=1>Temperature difference indegrees F.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>CHWSTFraction High</td><td rowspan=1 colspan=1>CHWSTFraction High = CHWSTNumberHigh/(CHWST Alarm Evaluation Interval). Thisis the fraction of the total number of time stepsduring the CHWST Alarm Evaluation Intervalthat have “Too High” as the value for thevariable CHWST Maintained OK/not.</td><td rowspan=1 colspan=1>Dimensionless real numberbetween 0.0 and 1.0.</td></tr><tr><td rowspan=1 colspan=1>CHWSTFraction Low</td><td rowspan=1 colspan=1>CHWSTFraction Low = CHWSTNumberLow/(CHWST Alarm Evaluation Interval). Thisis the fraction of the total number of timessteps during the CHWST Alarm EvaluationInterval that have “Too Low” as the value forthe variable CHWST Maintained OK/not.</td><td rowspan=1 colspan=1>Dimensionless real numberbetween 0.0 and 1.0.</td></tr><tr><td rowspan=1 colspan=1>CHWST Last</td><td rowspan=1 colspan=1>The value of the Chilled Water SupplyTemperature (CHWST) corresponding to thelast measurement time immediately precedingthe current measurement time.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>CHWST LowerBound</td><td rowspan=1 colspan=1>Chilled Water Supply Temperature LowerBound = CHW Setpoint - (CHWdDown). It isthe minimum CHW temperature consideredacceptably controlled.</td><td rowspan=1 colspan=1>Temperature difference indegrees F.</td></tr><tr><td rowspan=1 colspan=1>CHWST MaintainedOK/not (ChilledWater SupplyTemperatureMaintained OK/not)</td><td rowspan=1 colspan=1>Chilled Water Supply Temperature MaintainedOK/not is a variable indicating whether theCHW temperature is maintained adequately ata specific point in time (i.e., time step). It takesvalues of: &quot;OK,&quot; &quot;too high,&quot; and &quot;too low.&quot;</td><td rowspan=1 colspan=1>Ok, too high, or too low.</td></tr><tr><td rowspan=1 colspan=1>CHWST MaintainedOK/not Array</td><td rowspan=1 colspan=1>The array: {CHWST Maintained OK/not,CHWST Maintained OK/not (1 time step ago),CHWST Maintained OK/not (2 time steps ago),CHWST Maintained OK/not (3 time steps ago),CHWST Maintained OK/not (4 time steps ago),CHWST Maintained OK/not [(CHWST AlarmEvaluation Interval – 1) time steps ago]}</td><td rowspan=1 colspan=1>Array with individual elementstakings values of Ok or NotOK.</td></tr><tr><td rowspan=1 colspan=1>CHWST Mean Too-High Deviation</td><td rowspan=1 colspan=1>Arithmetic mean value of the CHWSTDeviation for times included in the CHWSTMaintained OK/not Array for which CHWSTMaintained OK/not is “Too High”</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>CHWST Mean Too-Low Deviation</td><td rowspan=1 colspan=1>Arithmetic mean value of the CHWSTDeviation for times included in the CHWSTMaintained OK/not Array for which CHWSTMaintained OK/not is “Too Low”.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>CHWSTNumber High</td><td rowspan=1 colspan=1>CHWSTNumber High is the number of valuesof the variable CHWST Maintained OK/not withvalues of “Too High” during the last CHWSTAlarm Evaluation Interval time steps.</td><td rowspan=1 colspan=1>Integer.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>CHWSTNumber Low</td><td rowspan=1 colspan=1>CHWSTNumber Low is the number of valuesof the variable CHWST Maintained OK/not withvalues of “Too Low” during the last CHWSTAlarm Evaluation Interval time steps.</td><td rowspan=1 colspan=1>Integer.</td></tr><tr><td rowspan=1 colspan=1>CHWST UpperBound</td><td rowspan=1 colspan=1>Chilled Water Supply Temperature UpperBound = CHW Setpoint + (CHWdup). It is themaximum CHW temperature consideredacceptably controlled.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>CHW Temperature</td><td rowspan=1 colspan=1>Chilled Water Temperature. Same as ChilledWater Supply Temperature.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>CHW TransientDecrease Factor</td><td rowspan=1 colspan=1>Fraction of the difference between the ChilledWater Supply Temperature (CHWST) at LastOff Time and the CHWST Setpoint that is usedto determine the Minimum Transient Decreasein CHWST. It takes values between 0 and 1.0and may be a user (setup) input, a defaultvalue, or a value determined empirically duringdiagnosis (i.e. use of the diagnostic tool).</td><td rowspan=1 colspan=1>Dimensionless real numberbetween 0.0 and 1.0</td></tr><tr><td rowspan=1 colspan=1>Compressor &quot;On&quot;Threshold</td><td rowspan=1 colspan=1>The value of Compressor Current (orCompressor Power) above which theCompressor is considered &quot;on.&quot; Used todetermine if the chiller is &quot;on.&quot;</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>Compressor Current(or Power)</td><td rowspan=1 colspan=1>The measured value of current (or power) atthe current time for the compressor motor.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>CompressorInterlocked WithCHW Pumps OK/not</td><td rowspan=1 colspan=1>An indicator of whether the compressor andthe CHW Pumps are properly interlocked ornot. It takes values of &quot;OK&quot; and &quot;Not OK.&quot;</td><td rowspan=1 colspan=1>OKNot OK.</td></tr><tr><td rowspan=1 colspan=1>CompressorInterlock withCondenser FansOK/Not</td><td rowspan=1 colspan=1>An indicator of whether the compressor andthe Condenser Fans are properly interlocked ornot. It takes values of &quot;OK&quot; and &quot;Not OK.&quot;</td><td rowspan=1 colspan=1>OKNot OK.</td></tr><tr><td rowspan=1 colspan=1>CompressorInterlocked WithCondenser PumpsOK/not</td><td rowspan=1 colspan=1>An indicator of whether the compressor andthe Condenser Pumps are properly interlockedor not. It takes values of &quot;OK&quot; and &quot;Not OK.&quot;</td><td rowspan=1 colspan=1>OKNot OK.</td></tr><tr><td rowspan=1 colspan=1>Compressor MotorRated Current (orPower)</td><td rowspan=1 colspan=1>Current (or power) rating of the compressormotor from the motor nameplate.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>Compressor OffCycle OK/not</td><td rowspan=1 colspan=1>An indicator of whether the compressor ismeeting the Minimum Compressor Off Timewhile cycling between off and on. It takesvalues of “OK” and “Not OK.”</td><td rowspan=1 colspan=1>OKNot OK.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Compressor OnCycle OK/not</td><td rowspan=1 colspan=1>An indicator of whether the compressor ismeeting the Minimum Compressor On Timewhile cycling between on and off. It takesvalues of “OK” and “Not OK.&quot;</td><td rowspan=1 colspan=1>OKNot OK.</td></tr><tr><td rowspan=1 colspan=1>Compressor On/offStatus</td><td rowspan=1 colspan=1>Same as Compressor status. An indicator ofwhether the compressor is on or off. Takesvalues of &quot;on&quot; or &quot;off.&quot; Chiller on/off Status =Compressor on/off Status.</td><td rowspan=1 colspan=1>On or off.</td></tr><tr><td rowspan=1 colspan=1>Compressor P</td><td rowspan=1 colspan=1>Fraction of Compressor Motor Rated Current(or Power) selected for the &quot;On&quot; Threshold</td><td rowspan=1 colspan=1>Dimensionless real numberbetween 0.0 and 1.0.</td></tr><tr><td rowspan=1 colspan=1>Compressor State</td><td rowspan=1 colspan=1>An indicator of whether the chiller is in an off, atransient, or a steady state, where thedifference between steady and transientoperation is indicated by the rate of change ofthe chilled water supply temperature (CHWST).Takes values of “Off,&quot;“Transient,&quot; or “Steady.&quot;</td><td rowspan=1 colspan=1>Off, transient, or steady.</td></tr><tr><td rowspan=1 colspan=1>Compressor Status</td><td rowspan=1 colspan=1>Same as Compressor On/off Status. Anindicator of whether the compressor (and,therefore the chiller) is on or off. Takes valuesof &quot;on&quot; or &quot;off” as indicated by the CompressorCurrent. Also indicates Chiller Status, i.e.,Chiller Status = Compressor Status.</td><td rowspan=1 colspan=1>On or off.</td></tr><tr><td rowspan=1 colspan=1>Condenser FanMotors RatedCurrent (or Power)</td><td rowspan=1 colspan=1>Current (or power) rating of the condenser fanmotors from the motor nameplates.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>Condenser Fans P</td><td rowspan=1 colspan=1>Fraction of Condenser Fan Motors RatedCurrent (or Power) selected for the &quot;On&quot;Threshold.</td><td rowspan=1 colspan=1>Dimensionless real numberbetween 0.0 and 1.0.</td></tr><tr><td rowspan=1 colspan=1>Condenser Fans&quot;On&quot; Threshold</td><td rowspan=1 colspan=1>The value of Condenser Fans Current (orPower) above which the condenser fans areconsidered &quot;on.&quot; Used to determine if thecondenser fans are &quot;on.&quot;</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>Condenser FansCurrent (or Power)</td><td rowspan=1 colspan=1>For air-cooled condensers, the measured valueof current (or power) for the condenser fans</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>Condenser FansStatus</td><td rowspan=1 colspan=1>For air-cooled chillers, an indicator of whetherthe condenser fans is (are) on or off. Takesvalues of &quot;on&quot; or &quot;off.&quot;</td><td rowspan=1 colspan=1>On or off.</td></tr><tr><td rowspan=1 colspan=1>Condenser Pumps P</td><td rowspan=1 colspan=1>Fraction of Condenser Pump Motors RatedCurrent (or Power) selected for the &quot;On&quot;Threshold</td><td rowspan=1 colspan=1>Current in amps.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Condenser Pumps&quot;On&quot; Threshold</td><td rowspan=1 colspan=1>The value of Condenser Pumps Current (orPower) above which the Condenser Pumps areconsidered &quot;on.&quot; Used to determine if thecondenser pumps are &quot;on.&quot;</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>Condenser PumpsCurrent (CPC)</td><td rowspan=1 colspan=1>The measured value of the electric current tothe chiller condenser pumps at the currenttime.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>Condenser PumpsCurrent (CPC)</td><td rowspan=1 colspan=1>The measured value of the electric current tothe chiller condenser pumps at the currenttime.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>Condenser PumpsCurrent (or Power)</td><td rowspan=1 colspan=1>Same as CPC.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>Condenser PumpsLast Time Turned On</td><td rowspan=1 colspan=1>The time of the last measurement ofCondenser Pumps Status at which theCondenser Pumps Status was &quot;On&quot; while thePreceding Condenser Pumps Status was &quot;Off.&quot;</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Condenser PumpsMax Start-Up Time</td><td rowspan=1 colspan=1>The maximum time that the condenser pumpsshould turn on before the compressor turns on.This can be set by default to 5 minutes.</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Condenser PumpsStatus</td><td rowspan=1 colspan=1>Variable indicating whether the condenserpumps are on or off</td><td rowspan=1 colspan=1>On or Off.</td></tr><tr><td rowspan=1 colspan=1>Condenser Type</td><td rowspan=1 colspan=1>Takes values of &quot;water cooled&quot; or &quot;air cooled.&quot;</td><td rowspan=1 colspan=1>Water cooled or air cooled.</td></tr><tr><td rowspan=1 colspan=1>Condenser-PumpsMotor Rated Current(or Power)</td><td rowspan=1 colspan=1>Current (or power) rating of the condenserpumps motor from the motor nameplate.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>CT ApproachBenchmark</td><td rowspan=1 colspan=1>An indicator of the maximum CT approachacceptable for the cooling tower whenproviding maximum cooling (i.e., when thesump temperature is at or above the setpointand the fans running continuously). Assumedto be available as a user input based on: 1)the control specification or 2) themanufacturer&#x27;s specification.</td><td rowspan=1 colspan=1>Temperature difference indegrees F.</td></tr><tr><td rowspan=1 colspan=1>CT Cycling OK/Not</td><td rowspan=1 colspan=1>Variable that indicates whether the cycling ofthe cooling tower fans is OK or not. If it cyclestoo frequently, the fan motors may bedamaged reducing their lives</td><td rowspan=1 colspan=1>OK or Not OK.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>CT Fan Motors RatedCurrent (or Power)</td><td rowspan=1 colspan=1>Cooling Tower Fan Motors Rated Current (orPower). Current (or power) rating of thecooling tower fan motors from the motornameplates.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>CT Fans Current (orPower</td><td rowspan=1 colspan=1>Cooling Tower Fans Current (or Power). Themeasured value of the electrical current (orpower) to the cooling tower fan motors at thecurrent time.</td><td rowspan=1 colspan=1>Amps.</td></tr><tr><td rowspan=1 colspan=1>CT Fans &quot;On&quot; SetPoint</td><td rowspan=1 colspan=1>The cooling tower “on” set point = the value ofthe sump temperature above which the coolingtower fans are turned on.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>CT Fans &quot;On&quot;Threshold</td><td rowspan=1 colspan=1>Cooling Tower Fans &quot;On&quot; Threshold. Thevalue of Cooling Tower Fans Current (orPower) above which the cooling tower fans areconsidered &quot;on.&quot; Used to determine if thecooling tower fans are &quot;on.&quot;</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>CT Fans “Off” SetPoint</td><td rowspan=1 colspan=1>The cooling tower “off” set point = the value ofthe sump temperature below which the coolingtower fans are turned off.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>CT Fans P</td><td rowspan=1 colspan=1>Cooling Tower Fans P. Fraction of CoolingTower Fan Motors Rated Current (or Power)selected for the &quot;On&quot; Threshold.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>CT Fans StagingOK/Not</td><td rowspan=1 colspan=1>Variable indicating whether the fan staging isOk or not.</td><td rowspan=1 colspan=1>&quot;OK (as far as we can tell).&quot;&quot;OK.&quot;&quot;Not OK. There is a fanstaging problem and thecooling tower is notmaintaining the Sump Tempas low as it could/should.&quot;&quot;Not OK. There is a fanstaging problem and energyis being wasted. All CT Fansshould be off.&quot;</td></tr><tr><td rowspan=1 colspan=1>CT Fans Status</td><td rowspan=1 colspan=1>Cooling Tower Fans Status. For water cooledchillers, a variable indicating whether thecooling tower fans are on or off. Takes valuesof &quot;on&quot; or &quot;off.&quot;</td><td rowspan=1 colspan=1>On or Off.</td></tr><tr><td rowspan=1 colspan=1>CT Fans/CondenserPumps InterlockOK/Not</td><td rowspan=1 colspan=1>An indicator of whether the cooling tower fansand the condenser pumps are properlyinterlocked or not.</td><td rowspan=1 colspan=1>OK or Not OK.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>CT Inlet Temperature</td><td rowspan=1 colspan=1>Temperature of the cooling water entering thecooling tower. This temperature will be veryclose to the temperature of the water leavingthe condenser of the chiller.</td><td rowspan=1 colspan=1>Temperature in degrees F</td></tr><tr><td rowspan=1 colspan=1>CT Range</td><td rowspan=1 colspan=1>Cooling Tower Range = The differencebetween the temperature of the water enteringthe cooling tower (cooling tower inlettemperature) and the temperature of the waterleaving the cooling tower (outlet temperature).</td><td rowspan=1 colspan=1>Temperature difference indegrees F.</td></tr><tr><td rowspan=1 colspan=1>CT RangeBenchmark</td><td rowspan=1 colspan=1>Benchmark for comparison of calculatedvalues of the CT range (may be a user inputbased on the control spec, specified by themanufacturer or determined by analysis ofoperating data. TBD)</td><td rowspan=1 colspan=1>Degrees F.</td></tr><tr><td rowspan=1 colspan=1>CT Range OK/Not</td><td rowspan=1 colspan=1>Variable indicating whether the CT rangecalculated from measurements is equal orgreater than the expected range (given by theCT Range Benchmark), in which case it is OK,or whether it is less than expected, in whichcase it is not OK because the cooling tower istransferring less heat at maximum capacitythan expected.</td><td rowspan=1 colspan=1>OK orNot OK. There is a problemwith CT heat rejection and itis performing at less thanexpected capacity.</td></tr><tr><td rowspan=1 colspan=1>CT Sump TempSetpoint</td><td rowspan=1 colspan=1>The setpoint for the water in the cooling towersump, i.e., the temperature setpoint for thewater leaving the cooling tower.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>CT SumpTemperature</td><td rowspan=1 colspan=1>The temperature of the cooling tower sump,which is the same as the temperature of thewater leaving the cooling tower of the coolingtower outlet temperature.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>Current Time</td><td rowspan=1 colspan=1>The time of the current time step</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Identification ofCondition</td><td rowspan=1 colspan=1>This data flow represents the collection of alloutput data from the diagnostic process(es),which characterize the condition of theequipment/systems undergoing diagnosis.This term is only used on the chiller contextdiagram. All other diagrams show individuadata flows.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Last Chilled WaterPumps Status (LastCHW Pumps Status)</td><td rowspan=1 colspan=1>The value of the CHW Pumps Status at themeasurement time immediately preceding thecurrent measurement time (i.e., at the lastmeasurement time).</td><td rowspan=1 colspan=1>On or Off</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Last Chiller Status</td><td rowspan=1 colspan=1>The value of Chiller Status at the measurementtime immediately preceding the currentmeasurement time (i.e., the last measurementtime). Last Chiller Status = Last CompressorStatus.</td><td rowspan=1 colspan=1>On or Off</td></tr><tr><td rowspan=1 colspan=1>Last CHWST forCompressor &quot;On&quot;Time</td><td rowspan=1 colspan=1>Chilled Water Supply Temperaturecorresponding to the last measurement timewhen the compressor was on immediatelypreceding the current measurement time.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>Last Compressor OffInterval</td><td rowspan=1 colspan=1>The length of time the compressor was off thelast time it was off. Last Compressor OffInterval = Last Compressor Switch On Time –Last Compressor Switch Off Time. Onlyevaluated when the compressor is currently on.</td><td rowspan=1 colspan=1>Time difference in minutes.</td></tr><tr><td rowspan=1 colspan=1>Last CompressorSwitch Off Time</td><td rowspan=1 colspan=1>The last time at which the Compressor turnedoff, i.e., the last measurement time at which theCompressor Status changed from “On” to “Off.&quot;</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Last Compressor OnInterval</td><td rowspan=1 colspan=1>The length of time the compressor was on thelast time it was on. Last Compressor OnInterval = Last Compressor Off Time – LastCompressor On Time. Only evaluated whenthe compressor is currently off.</td><td rowspan=1 colspan=1>Time difference in minutes.</td></tr><tr><td rowspan=1 colspan=1>Last CompressorSwitch On Time</td><td rowspan=1 colspan=1>The last time at which the Compressor turnedon, i.e., the last measurement time at which theCompressor Status changed from “Off” to “On.&quot;</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Last CompressorState</td><td rowspan=1 colspan=1>The value of Compressor State at themeasurement time immediately preceding thecurrent measurement time (i.e., the lastmeasurement time).</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Last CompressorStatus</td><td rowspan=1 colspan=1>The value of Compressor Status at themeasurement time immediately preceding thecurrent measurement time (i.e., the lastmeasurement time). Last Compressor Status =Last Chiller Status.</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Last CondenserPumps Status</td><td rowspan=1 colspan=1>The value of Condenser Pumps Status at themeasurement time immediately preceding thecurrent measurement time (i.e., the lastmeasurement time).</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Last CT Fan OffInterval</td><td rowspan=1 colspan=1>The length of time the CT fans were off the lasttime they were off. Last CT Fan Off Interval =Last CT Fans On Time – Last CT Fans OffTime. Only evaluated when the compressor iscurrently on.</td><td rowspan=1 colspan=1>Time difference in minutes.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Last CT Fans OffTime</td><td rowspan=1 colspan=1>The last time at which the CT Fans turned on,i.e., the last measurement time at which the CTfans status changed from “Off” to “On.&quot;</td><td rowspan=1 colspan=1>Absolute time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Last CT Fans OnTime</td><td rowspan=1 colspan=1>The last time at which the CT Fans turned off,i.e., the last measurement time at which the CTfans status changed from “On” to “Off.&quot;</td><td rowspan=1 colspan=1>Absolute time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Last CT Fans Status</td><td rowspan=1 colspan=1>The value of the CT fans status at themeasurement time immediately preceding thecurrent measurement time (i.e., at the lastmeasurement time).</td><td rowspan=1 colspan=1>On or Off.</td></tr><tr><td rowspan=1 colspan=1>Last Fans On Interval</td><td rowspan=1 colspan=1>The length of time the CT fans were on the lasttime they were on. Last CT Fan On Interval =Last CT Fans Off Time – Last CT Fans onTime. Only evaluated when the compressor iscurrently off.</td><td rowspan=1 colspan=1>Time difference in minutes.</td></tr><tr><td rowspan=1 colspan=1>Measurement Time</td><td rowspan=1 colspan=1>The time at which measured (or metered) dataare collected.</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Metered Data</td><td rowspan=1 colspan=1>The collection of all input data that is collectedperiodically from sensors or observationsValues of metered data are updatedperiodically at the measurement frequency. Itcan be contrasted with set-up data, which isgenerally collected only once. Metered data isgenerally used to characterize the condition (orstate) of the equipment and systems at aparticular point in time. This term is used onlyon the chiller context diagram. All otherdiagrams show individual data flows.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Min. CT Fans OffTime</td><td rowspan=1 colspan=1>The minimum permissible time increment thatthe cooling tower fans should be off beforebeing turned on again in order to preventdamage to the fan motors during fan cycling,as specified by the manufacturer.</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Min. CT Fans OnTime</td><td rowspan=1 colspan=1>The minimum permissible time increment thatthe cooling tower fans should be on beforebeing turned off again in order to preventdamage to the fan motors during fan cycling,as specified by the manufacturer.</td><td rowspan=1 colspan=1>Time in minutes.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>MinimumCompressor Off Time</td><td rowspan=1 colspan=1>The minimum time specified by themanufacturer (or other authority) that thecompressor should be off before being turnedback on again.</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>MinimumCompressor On Time</td><td rowspan=1 colspan=1>The minimum time specified by themanufacturer (or other authority) that thecompressor should be on before being turnedback off again.</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Minimum TransientDecrease in CHWST</td><td rowspan=1 colspan=1>The minimum transient decrease in the chilledwater supply temperature. This is theminimum change in chilled water supplytemperature between two sequentialmeasurement times that would be judged ascorresponding to a transient compressor state.All values of the change in CHWST betweentwo successive measurement times would bejudged as corresponding to a steady state forthe compressor.</td><td rowspan=1 colspan=1>Temperature difference in F.</td></tr><tr><td rowspan=1 colspan=1>OAT Steady StateCHW</td><td rowspan=1 colspan=1>Outdoor-Air Temperature while the ChilledWater Temperature is in a steady state, i.e.,when Compressor State = Steady.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>Outdoor-AirTemperature (OAT)</td><td rowspan=1 colspan=1>Equivalent to Ambient-Air Temperature (OAT)and is the dry -bulb temperature of the ambientoutdoor air.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>Outdoor-AirTemperature WetBulb (OATWB)</td><td rowspan=1 colspan=1>Wet-bulb temperature of the outdoor air.Equivalent to Ambient Wet-Bulb Temperatureand Outdoor-Air Wet-Bulb Temperature</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>Outdoor-Air Wet-Bulb Temperature(OATWB)</td><td rowspan=1 colspan=1>Wet-bulb temperature of the outdoor air.Equivalent to Ambient Wet-Bulb Temperatureand Outdoor-Air Temperature Wet Bulb(OATWB)</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>Passed (Filtered) CTApproach</td><td rowspan=1 colspan=1>Values of the CT approach for times when thecondenser pumps status is “on”</td><td rowspan=1 colspan=1>Temperature difference indegrees F</td></tr><tr><td rowspan=1 colspan=1>Passed (Filtered)Ambient wb Temp</td><td rowspan=1 colspan=1>Values of the Ambient wb temperature fortimes when the condenser pump status is “on”</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>Passed (Filtered) CTSump Temp</td><td rowspan=1 colspan=1>Values of the sump temperature for timeswhen the condenser pumps are on.</td><td rowspan=1 colspan=1>Temperature in degrees F</td></tr><tr><td rowspan=1 colspan=1>Passed (Filtered) CTRange</td><td rowspan=1 colspan=1>Values of the CT range for times when thecondenser pumps status is “on”</td><td rowspan=1 colspan=1>Temperature difference indegrees F</td></tr><tr><td rowspan=1 colspan=1>Passed (Filtered) CTFans Current</td><td rowspan=1 colspan=1>Values of the Fans Current for times when thecondenser pumps are on.</td><td rowspan=1 colspan=1>Current in amps</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Passed (Filtered) CTFans Current</td><td rowspan=1 colspan=1>Values of the CT Fans Current occurring whenthe Condenser Pumps status is “on”(i.e.,belong to triplets for which Condenser PumpsStatus = On).</td><td rowspan=1 colspan=1>Current in amps</td></tr><tr><td rowspan=1 colspan=1>Passed (Filtered) CTFans Status</td><td rowspan=1 colspan=1>Values of the CT Fans Status occurring whenthe Condenser Pumps status is “on”(i.e.,belong to triplets for which Condenser PumpsStatus = On).</td><td rowspan=1 colspan=1>OnOff</td></tr><tr><td rowspan=1 colspan=1>Passed Ambient wbTemp Points forCondenser PumpsOn,CT Fans Status On,and Sump TempAbove the CT Fans&quot;On&quot; Setpoint</td><td rowspan=1 colspan=1>Values of the ambient wb temperature fortimes when the condenser pumps are on, theCT fans status is on, and the sumptemperature is above its setpoint</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>Passed CT Range forCondenser PumpsOn,CT Fans Status On,andSump Temp Abovethe ČT Fans &quot;On&quot;Setpoint</td><td rowspan=1 colspan=1>Values of the CT Range for times when thecondenser pumps are on, the CT fans status ison, and the sump temperature is above itssetpoint</td><td rowspan=1 colspan=1>Temperature difference indegrees F</td></tr><tr><td rowspan=1 colspan=1>PrecedingCondenser PumpsStatus</td><td rowspan=1 colspan=1>The Condenser Pumps Status at themeasurement time immediately preceding themeasurement time to which reference is made.</td><td rowspan=1 colspan=1>On or Off.</td></tr><tr><td rowspan=1 colspan=1>Rejected Ambient wbTemp Points for CTFans Status Offand/or for SumpTemp Below the CTFans &quot;On&quot; Setpoint</td><td rowspan=1 colspan=1>Values of the ambient temperature thatcorrespond to times when the condenserpumps are on and either or both the CT fansstatus are off or the sump temperature is belowor equal to its setpoint.</td><td rowspan=1 colspan=1>Temperature in degrees F</td></tr><tr><td rowspan=1 colspan=1>Rejected Ambient wbTemp WhenCondenser Pumpsare &quot;Off&quot;</td><td rowspan=1 colspan=1>Values of ambient wb temperature thatcorrespond to times when the condenserpumps are off, which are filtered out</td><td rowspan=1 colspan=1>Temperature in degrees F</td></tr><tr><td rowspan=1 colspan=1>Rejected CHWST forNon-Steady CHWST</td><td rowspan=1 colspan=1>Rejected values of CHWST corresponding totimes when the Compressor State =“Transient”, or Compressor State = “Off”, i.e.,when the CHWST is not steady.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>Rejected CTApproach andAmbient wb TempWhen CondenserPumps are &quot;Off&quot;</td><td rowspan=1 colspan=1>Values of CT Approach and Ambient wbTemperature that correspond to times whenthe condenser pumps are off, which are filteredout</td><td rowspan=1 colspan=1></td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Rejected CTApproach andAmbient wb TempPoints for CT FansStatus Off and/or forSump Temp Belowthe CT Fans &quot;On&quot;Setpoint</td><td rowspan=1 colspan=1>Values of the CT Approach and ambienttemperature that correspond to times when theCT fans status is “off” and/or the sumptemperature is below the CT Fans “On” setpoint.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Rejected CT FansCurrent WhenCondenser Pumpsare &quot;Off&quot;</td><td rowspan=1 colspan=1>Values of the CT Fans Current for times whenthe condenser pumps are off.</td><td rowspan=1 colspan=1>Current in amps</td></tr><tr><td rowspan=1 colspan=1>Rejected CT Rangefor CT Fans StatusOff and/or SumpTemp Below theCT Fans &quot;On&quot;Setpoint</td><td rowspan=1 colspan=1>Values of the CT Range that correspond totimes when the condenser pumps are on andeither or both the CT fans status is off or thesump temperature is below or equal to itssetpoint.</td><td rowspan=1 colspan=1>Temperature difference indegrees F</td></tr><tr><td rowspan=1 colspan=1>Rejected CT RangeWhen CondenserPumps are &quot;Off&quot;</td><td rowspan=1 colspan=1>Values of CT Range that correspond to timeswhen the condenser pumps are off, which arefiltered out</td><td rowspan=1 colspan=1>Temperature difference indegrees F</td></tr><tr><td rowspan=1 colspan=1>Rejected CT SumpTemp WhenCondenser Pumpsare &quot;Off&quot;</td><td rowspan=1 colspan=1>Values of the Sump Temperature at timeswhen the condenser pumps are off</td><td rowspan=1 colspan=1>Temperature in degrees F</td></tr><tr><td rowspan=1 colspan=1>Rejected OAT forNon-Steady CHWST</td><td rowspan=1 colspan=1>Rejected values of OAT corresponding to timeswhen the Compressor State = “Transient” orCompressor State = “Off”, i.e., when theCHWST is not steady.</td><td rowspan=1 colspan=1>Temperature in degrees F.</td></tr><tr><td rowspan=1 colspan=1>Secondary CHWPumps CollectiveStatus</td><td rowspan=1 colspan=1>The status of all the secondary chilled waterpumps in an associated set taken as a singleunit. If at least one pump of the set is ON, thecollective status is ON. If all the pumps in theset are OFF, the collective status is OFF.</td><td rowspan=1 colspan=1>On or Off.</td></tr><tr><td rowspan=1 colspan=1>Secondary CHWPumps Motor RatedCurrent (or Power)</td><td rowspan=1 colspan=1>Secondary Chilled Water Pumps Motor RatedCurrent (or Power). Current (or power) ratingof the secondary CHW pump motor from themotors nameplate(s).</td><td rowspan=1 colspan=1>Current in amps.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Secondary CHWPumps &quot;On&quot;Threshold</td><td rowspan=1 colspan=1>The value of Secondary CHW Pumps Current(or Power) above which the secondary CHWPumps is considered &quot;on.&quot; Used to determineif the secondary chilled water Pumps is (are)&quot;on.&quot;</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>Secondary CHWPumps P</td><td rowspan=1 colspan=1>Secondary Chilled Water Pumps P. Fraction ofSecondary Chilled Water Pumps Motors RatedCurrent (or Power) selected for the &quot;On&quot;Threshold.</td><td rowspan=1 colspan=1>Dimensionless real numberbetween 0.0 and 1.0.</td></tr><tr><td rowspan=1 colspan=1>Secondary CHWPumps Current (orPower)</td><td rowspan=1 colspan=1>The measured value of current (or power) forthe secondary CHW Pumps at the current time.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>Secondary/PrimaryCHW PumpsInterlock OK/not</td><td rowspan=1 colspan=1>For chilled water distribution systems withsecondary CHW pumps. An indicator ofwhether the primary CHW pumps and thesecondary CHW pumps served by it areproperly interlocked or not. It takes values of&quot;OK&quot; and &quot;Not OK.&quot;</td><td rowspan=1 colspan=1>Ok.Not Ok.</td></tr><tr><td rowspan=1 colspan=1>Set-up Data</td><td rowspan=1 colspan=1>The collection of all input data thatcharacterizes the equipment and systems inplace in the building as well as its performance.It is generally entered only once for a specificbuilding or specific piece of equipment and canbe contrasted with metered data which iscollected periodically. This term is used only onthe chiller context diagram. All other diagramsshow individual data flows.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Sump Temp ControlOK/Not</td><td rowspan=1 colspan=1>A variable indicating whether the sumptemperature control is OK or not at the currenttime</td><td rowspan=1 colspan=1>OKNot OK. The CT fans are offbut should be on.Not OK. The CT fans are onbut should be off.</td></tr><tr><td rowspan=1 colspan=1>Supply Fan MotorsRated Current (orPower)</td><td rowspan=1 colspan=1>Current (or power) rating of the supply fanmotors from the motor nameplates.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>Supply Fans Status</td><td rowspan=1 colspan=1>An indicator of whether the supply fans are onor off. Takes values of &quot;on&quot; or &quot;off.&quot;</td><td rowspan=1 colspan=1>On or off</td></tr><tr><td rowspan=1 colspan=1>Supply Fans &quot;On&quot;Threshold</td><td rowspan=1 colspan=1>The value of Supply Fans Current (or Power)above which the supply fans are considered&quot;on.&quot; Used to determine if the supply fans are&quot;on.&quot;</td><td rowspan=1 colspan=1>Current in amps.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Supply Fans Current(or Power)</td><td rowspan=1 colspan=1>The measured value of current (or power) forthe supply fans.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>Supply Fans P</td><td rowspan=1 colspan=1>Fraction of Supply Fan Motors Rated Current(or Power) selected for the &quot;On&quot;Threshold.</td><td rowspan=1 colspan=1>Dimensionless real numberbetween 0.0 and 1.0.</td></tr><tr><td rowspan=1 colspan=1>SupplyFans/SecondaryCHW PumpsInterlock OK/not</td><td rowspan=1 colspan=1>For chilled water distribution systems withsecondary pumps. An indicator of whether thesecondary CHW pumps and the supply fans forthe air handlers served by them are properlyinterlocked or not. It takes values of &quot;OK,&quot; &quot;NotOK,&quot; and &quot;Possible problem with supply fancontrol--check to see if loads in the spacesserved are being met.&quot;</td><td rowspan=1 colspan=1>Ok.Not Ok.Not OK,&quot; and &quot;Possibleproblem with supply fancontrol--check to see if loadsin the spaces served arebeing met.</td></tr><tr><td rowspan=1 colspan=1>Supply Fans/CHWPumps InterlockOK/not</td><td rowspan=1 colspan=1>An indicator of whether the primary CHWpumps and the supply fans for the air handlersserved by them are properly interlocked or not.It takes values of &quot;OK,&quot; &quot;Not OK,&quot; and&quot;Possible problem with supply fan control--check to see if loads in the spaces served arebeing met&quot;</td><td rowspan=1 colspan=1>Ok.Not Ok.Possible problem with supplyfan control--check to see ifloads in the spaces servedare being met.</td></tr><tr><td rowspan=1 colspan=1>Total Number ofTime StepsProcessed</td><td rowspan=1 colspan=1>The total number of time steps for whichprocessing has been performed sinceprocessing was started and up to the currenttime. It takes integer values.</td><td rowspan=1 colspan=1>Integer.</td></tr><tr><td rowspan=1 colspan=1>Water sideEconomizing</td><td rowspan=1 colspan=1>Variable that indicates whether water sideeconomizing is used or not.</td><td rowspan=1 colspan=1>YesNo</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

6. Appendix C: Data Flow Diagrams for Boiler Diagnostic Processes

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

Context Diagram Boiler

![](images/df0551539f4e47cf8050f4c8b66b0e2e0d35d7a41998ee6a575d479f8b5c8661.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

![](images/7dd10951177e2ac771dab0323e1086aae3fefd42654646aff6404ee3c9df905f.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 1.0 Diagnose Boiler Shutoff

![](images/db4e1acb05127c1e9353d721f0e282af6a964bfe101ffed8f77d2f8f8f3e5270.jpg)  
Note: No diagnosis is provided for Ambient-Temperature-Based or other temperature-based boiler shutoffs. Further develelopment is required for these diagnostic procedures.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 1.1 Diagnose Always-On-Boiler Shutoff

If Boiler\_Schedule\_Type = "Always On" AND Boiler\_Status = "On" Set Boiler\_Shutoff $. O K / N o t = " O K .$ The boiler is on as it should be. Shutoff is not applicable to this boiler. The boiler system is designed for continous operation."

If Boiler\_Schedule\_Type = "Always On" AND Boiler\_Status = "Off" Set Boiler\_Shutoff\_OK/Not = "Not OK; the boiler is off and it should be on always, unless it is locked out temporarily for maintenance or repair."

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 1.2 Diagnose Manual-shutoff-Boiler Shutoff

```csv
If Boiler_Schedule_Type = "Manual Shutoff" AND Boiler_Status = "On"
AND if Current_Date > Boiler_On_Date + Boiler_On_Date_dUp
Set Boiler_Shutoff_OK/Not = "OK; the boiler is on as it should be."
If Boiler_Schedule_Type = "Manual Shutoff" AND Boiler_Status = "Off"
AND if Current_Date > Boiler_On_Date + Boiler_On_Date_dUp
Set Boiler_Shutoff_OK/Not = "Not OK; the boiler is off when it should be on."
If Boiler_Schedule_Type = "Manual Shutoff" AND Boiler_Status = "On"
AND if Current_Date < Boiler_Off_Date - Boiler_Off_Date_dDown,
Set Boiler_Shutoff_OK/Not = "OK; the boiler is on as it should be."
If Boiler_Schedule_Type = "Manual Shutoff" AND Boiler_Status = "Off"
AND if Current_Date < Boiler_Off_Date - Boiler_Off_Date_dDown,
Set Boiler_Shutoff_OK/Not = "Not OK; the boiler is off when it should be on."
If Boiler_Schedule_Type = "Manual Shutoff" AND Boiler_Status = "Off"
AND If Current_Date < Boiler_On_Date - Boiler_On_Date_dDown,
AND If Current_Date > Boiler_Off_Date + Boiler_Off_Date_dUp,
Set Boiler_Shutoff_OK/Not = "OK; the boiler is off as it should be"
If Boiler_Schedule_Type = "Manual Shutoff"
AND If Current_Date > Boiler_On_Date - Boiler_On_Date_dDown,
AND If Current_Date < Boiler_On_Date + Boiler_On_Date_dUp,
Set Boiler_Shutoff_OK/Not = "Ok; the date is too close to the Boiler On Date to evaluate
compliance with the schedule."
If Boiler_Schedule_Type = "Manual Shutoff"
AND If Current_Date > Boiler_Off_Date - Boiler_Off_Date_dDown,
AND If Current_Date < Boiler_Off_Date + Boiler_Off_Date_dUp,
Set Boiler_Shutoff_OK/Not = "Ok; the date is too close to the Boiler Off Date to evaluate
compliance with the schedule."
```

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 2.0 Diagnose Hot Water Temperature Control

![](images/4c2ffade571652000856965594384ce34832713b5138da0547ed48a829ed838c.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 2.1 Evaluate Current Hot Water Temperature

Calculate the upper bound for acceptable Hot Water Supply Temperature using

$$
{ \sf H W S T } \ { \sf U p p e r \ B o u n d } = { \sf H W S T } \_ { \sf S e t p o i n t - C u r r e n t + H W S T \_ d U p }
$$

Calculate the lower bound for acceptable Hot Water Supply Temperature using

$$
\mathsf { H W S T L o w e r B o u n d } = \mathsf { H W S T \_ S e t p o i n t } \cdot \mathsf { C u r r e n t } \cdot \mathsf { H W S T \_ d D o w n }
$$

Compare the Hot Water Supply Temperature (HWST) to the HWST Upper Bound and HWST Lower Bound.

If HWST > HWST Upper Bound, then   
Set HWST-SP\_Maintained\_OK/Not = "Too high" for the current time.

If HWST < HWST Lower Bound, then

If HWST <= HWST Upper Bound, AND

Calculate the HWST Deviation for the current time

HWST\_Deviation = HWST - HWST\_Setpoint-Current.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

2.2 Evaluate Long-Term HWST Control

![](images/77365b712d8287e1cf09a0faa98eed02465a3f983dedde2d48c3ef254d3abdb6.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 2.2.1 Update Hot Water Temp Low Alarm Variables

Update the Time\_Steps\_Processed, using

Time\_Steps\_Processed = Time\_Steps\_Processed + 1

Update the value of FHWST\_Low based on the latest value of HWST\_Maintained\_OK/Not.

Update the HWST\_Maintained\_OK/not\_Too-Low\_Array

Update all values in the array, adding the current value of HWST\_Maintained\_OK/not to the array and by dropping the oldest value of HWST\_Maintained\_OK/not from the array.

Update value for HWSTNumber\_Low.

Set HWSTNumber\_Low = number of values "Too Low" appearing in HWST\_Maintained OK/Not\_Too-Low\_Array.

If Total\_Number\_of\_Time\_Steps\_Processed < HWST\_Too\_Low\_Window, then set HWSTNumber\_Low = 0.

Calculate the new value of FHWST\_Low.

$$
\mathsf { F H W S T \_ L o w } = \mathsf { H W S T N u m b e r \_ L o w } / ( \mathsf { H W S T \_ T o o \_ L o w } \_ \mathsf { W i n d o w } )
$$

If FHWST\_High < FHWST\_HIgh\_Limit, AND   
FHWST\_Low < FHWST\_Low\_Limit,   
Set HWST\_Maintained\_OK/Not = "OK"

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 2.2.2 Evaluate Hot-Water Temperature Alarm Conditions

Check if the long-term average hot-water supply tempeature (HWST) is adequately maintained or whether it is high or low by comparing FHWST\_High and FHWST\_Low with thir repective limits.

If FHWST\_High >= FHWST\_High\_Limit, Set HWST\_Maintained\_OK/Not = "Too high"

$$
\begin{array} { r l } & { \mathsf { I f } \mathsf { F H W S T \_ L o w } > = \mathsf { F H W S T \_ L o w } \_ \mathsf { L i m i t } , } \\ & { \mathsf { S e t } \mathsf { H W S T \_ M a i n t a i n e d \_ O K } \mathsf { I N o t } = \mathsf { w T o o } \mathsf { l o w } " } \end{array}
$$

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 2.2.3 Update Hot Water Temp High Alarm Variables

Update the value of FHWST\_High based on the latest value of HWST\_Maintained\_OK/Not.

Update the HWST\_Maintained\_OK/not\_Too-High\_Array

Update all values in the array, adding the current value of HWST\_Maintained\_OK/not to the array and by dropping the oldest value of HWST\_Maintained\_OK/not from the array.

Update value for HWSTNumber\_High.

Set HWSTNumber\_High = number of values "Too High" appearing in HWST\_Maintained\_OK/ not\_Too-High\_Array.

If Total Number of Time Steps Processed < HWST\_Too\_High\_Window, then set HWSTNumber\_High = 0.

Calcluate the new value of FHWST\_High.

$$
\mathsf { F H W S T \_ H i g h } = \mathsf { H W S T N u m b e r \_ H i g h } / ( \mathsf { H W S T \_ T o o \_ H i g h \_ W i n d o w } )
$$

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

3.0 Diagnose Boiler Cycling

![](images/c001eee1dfe0b113d4fc85594dfa40d3f5037530f7ce86a6490db6e7ca010a06.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 3.2 Calculate On and Off Duration and Cycles

Calculate Latest\_Complete\_Boiler\_On\_Duration   
If Boiler\_Status = "On"   
Set Latest\_Complete\_Boiler\_On\_Duration = Boiler\_Last\_Off\_Time - Boiler\_NextTo\_Last\_On\_Time   
If Boiler\_Status = "Off"   
Set Latest\_Complete\_Boiler\_On\_Duration = Boiler\_Last\_Off\_Time - Boiler\_Last\_On\_Time   
Calculate Latest\_Complete\_Boiler\_Off\_Duration   
If Boiler\_Status = "Off"   
Set Latest\_Complete\_Boiler\_Off\_Duration = Boiler\_Last\_On\_Time - Boiler\_NextTo\_Last\_Off\_Time   
If Boiler\_Status = "On"   
Set Latest\_Complete\_Boiler\_Off\_Duration = Boiler\_Last\_On\_Time - Boiler\_Last\_Off\_Time

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 3.3 Diagnose Boiler Cycling Behavior

If Boiler\_Cycles\_Past\_Hour > Max\_Normal\_Boiler\_CPH, AND   
Latest\_Complete\_Boiler\_On\_Duration < Min\_Normal\_Boiler\_On\_Duration AND   
Latest\_Complete\_Boiler\_Off\_Duration < Min\_Normal\_Boiler\_Off\_Duration,   
then set Boiler\_Cycling\_OK/Not = "Not OK. The Boiler is cycling on and off   
excessively."   
If Boiler\_Cycles\_Past\_Hour > Max\_Normal\_Boiler\_CPH, AND   
Latest\_Complete\_Boiler\_On\_Duration < Min\_Normal\_Boiler\_On\_Duration, AND   
Latest\_Complete\_Boiler\_Off\_Duration >= Min\_Normal\_Boiler\_Off\_Duration,   
then set Boiler\_Cycling\_OK/Not = "Not OK. The Boiler is cycling on excessively."   
If Boiler Cycles Past Hour > Max\_Normal\_Boiler\_CPH AND   
Latest\_Complete\_Boiler\_On\_Duration >= Min\_Normal\_Boiler\_On\_Duration, AND   
Latest\_Complete\_Boiler\_Off\_Duration < Min\_Normal\_Boiler\_Off\_Duration,   
then set Boiler\_Cycling\_OK/Not = "Not OK. The Boiler is cycling off excessively."   
If Boiler Cycles Past Hour <= Max\_Normal\_Boiler\_CPH,   
then set Boiler\_Cycling\_OK/Not = "OK."

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 3.4 Calcluate boiler cycles per hour

Set number of time steps in an hours   
Set Nmax = 60/TimeStep   
Update Boiler\_Status\_Array   
Boiler\_Status(Current\_time - Nmax \* TimeStep) = Boiler\_Status[Current\_time - (Nmax - 1) \* TimeStep]   
Boiler\_Status[Current\_time - (Nmax - 1) \* TimeStep] = Boiler\_Status[Current\_time - (Nmax - 2) \* TimeStep]   
Boiler\_Status(Current\_time - 2 \* TimeStep) = Boiler\_Status(Current\_time - TimeStep)   
Boiler\_Status(Current\_time - TimeStep) = Boiler\_Last\_Status   
Boiler\_Status(Current\_time) = Boiler\_Status   
Calculate Boiler\_Cycles\_Past\_Hour.   
Assign BSNumber(nt) for all values of nt from -Nmax to 0,   
If Boiler\_Status = "On," set BSNumber(nt) = 1.   
If Boiler\_Status = "Off," set BSNumber(nt) = 0.   
Set Cycle\_Counts = 0   
Evaluate the following for each value of nt for -Nmax <= nt <= 0   
(zero corresponding to the current time and -Nmax corresonding to Nmax time steps ago)   
If Boiler\_Status(Current\_time) = "Off" AND BSNumber(nt+1) - BSNumber(nt) < 0   
Set Cycle\_Counts = Cycle\_Counts + 1   
If Boiler\_Status(Current\_time) = "Off" AND BSNumber(nt+1) - BSNumber(nt) >= 0   
Set Cycle\_Counts = Cycle\_Counts   
If Boiler\_Status(Current\_time) = "On" AND BSNumber(nt+1) - BSNumber(nt) > 0   
Set Cycle\_Counts = Cycle\_Counts + 1   
If Boiler\_Status(Current\_time) = "On" AND BSNumber(nt+1) - BSNumber(nt) <= 0   
Set Cycle\_Counts = Cycle\_Counts   
If nt < 0, repeat for next value of nt.   
If nt = 0, Set Boiler\_Cycles\_Past\_Hour = Cycle\_Counts - 1   
Note: We can probably specify more efficient ways to update the variables used in this cycle coutning procedure.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

4.0 Determine Boiler State

![](images/7c23feba0c90126478c6fc71640eafd33059e05d4c590411b9a2267200012a03.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 4.1 Determine Boiler On Threshold

Determine the Boiler Type and set corresponding Boiler "On" threshold.

If Boiler\_Fuel = Electric, then   
Set Boiler\_On\_Threshold\_Electric = Boiler\_On\_Threshold\_Electric\_P \*   
Boiler\_Capacity, and   
Set Boiler\_On\_Threshold\_Fossil = null

If the Boiler\_Fuel = Fossil, then   
Set Boiler\_On\_Threshold\_Fossil = (Design\_HWST + 75 )/2, and   
Set Boiler\_On\_Threshold \_Electric = null

If Boiler\_Stage\_Power <= Boiler On Threshold Electric,   
Set Boiler\_Status = "Off"

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 4.2 Determine Boiler Status

Update Boiler\_Last\_Status,

Boiler\_Last\_Status = Boiler\_Status

Check if the boiler on thresholds are exceeded. and set the boiler status accordingly.

If Boiler\_Stage\_Power > Boiler On Threshold Electric, then   
set Boiler\_Status = "On"

Otherwise,

If HWST <= Boiler On Threshold Fossil,   
Set Boiler\_Status = "Off"

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 4.3 Determine Boiler Last On and Off Times

Calculate Boiler\_Last\_On\_Time   
If Boiler\_Status = "On" and "Boiler\_Last\_Status = "Off," then   
Set Boiler\_NextTo\_Last\_On\_Time = Boiler\_Last\_On\_Time   
Set Boiler\_Last\_On\_Time = Current\_Time   
If Boiler\_Status = "On" and "Boiler\_Last\_Status = "On," then   
Set Boiler\_Last\_On\_Time = Boiler\_Last\_On\_Time   
[Note: No change in value of Boiler\_Last\_On\_Time.]   
If Boiler\_Status = "Off" and "Boiler\_Last\_Status = "Off," then   
Set Boiler\_Last\_On\_Time = Boiler\_Last\_On\_Time   
[Note: No change in value of Boiler\_Last\_On\_Time.]   
If Boiler\_Status = "Off" and "Boiler\_Last\_Status = "On," then   
Set Boiler\_Last\_On\_Time = Boiler\_Last\_On\_Time   
[Note: No change in value of Boiler\_Last\_On\_Time.]   
Calculate Boiler\_Last\_Off\_Time   
If Boiler\_Status = "Off" and "Boiler\_Last\_Status = "On," then   
Set Boiler\_NextTo\_Last\_Off\_Time = Boiler\_Last\_Off\_Time   
Set Boiler\_Last\_Off\_Time = Current\_Time   
If Boiler\_Status = "Off" and "Boiler\_Last\_Status = "Off," then   
Set Boiler\_Last\_Off\_Time = Boiler\_Last\_Off\_Time   
[Note: No change in value of Boiler\_Last\_Off\_Time.]   
If Boiler\_Status = "On" and "Boiler\_Last\_Status = "On," then   
Set Boiler\_Last\_Off\_Time = Boiler\_Last\_Off\_Time   
[Note: No change in value of Boiler\_Last\_Off\_Time.]   
If Boiler\_Status = "On" and "Boiler\_Last\_Status = "Off," then   
Set Boiler\_Last\_Off\_Time = Boiler\_Last\_Off\_Time   
[Note: No change in value of Boiler\_Last\_Off\_Time.]   
Battelle Northwest, 2003 Page 158

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 5.0 Diagnose HW Pump Shutoff

If Boiler\_Status = "Off" AND HW\_Pump\_Status = "Off"   
Set HW\_Pump\_Shutoff\_OK/Not = "OK; the hot-water pump is off as it should be."   
If Boiler\_Status = "On" AND HW\_Pump\_Status = "On"   
Set HW\_Pump\_Shutoff\_OK/Not = "OK; the hot-water pump is on while the boiler is on."   
If Boiler\_Schedule\_Type = "Ambient Shutoff" OR "Manual Shutoff" AND   
Boiler\_Status = "Off" AND   
HW\_Pump\_Status = "On" AND   
Current\_time - Boiler\_Last\_On\_Time <= HW\_Pump\_Run\_Limit, then   
Set HW\_Pump\_Shutoff\_OK/Not = "OK; the hot-water pump is running while the boiler is off, but   
the hot-water run limit has not been exceeded yet."   
If Boiler\_Schedule\_Type = "Ambient Shutoff" OR "Manual Shutoff" AND   
Boiler\_Status = "Off" AND   
HW\_Pump\_Status = "On," AND   
Current\_time - Boiler\_Last\_On\_Time > HW\_Pump\_Run\_Limit, then   
Set HW\_Pump\_Shutoff\_OK/Not = "Not OK; the hot-water pump is running unnecessarily,   
wasting energy, and unnecessarily reducing its remaining operating life."   
Note: No diagnostics are provided for HW Pump off while boiler is on. This requires further   
development. This situation can also present a safety problem so it is important from a safety standpoint   
as well as efficient operation. Additional diagnostics are needed.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

6.0 Determine Hot-Water Pump State

![](images/7c797f1c27bfe73cf5708e7cd9546f5c509cb18c6f9e8132b8018fc4f2b83fd0.jpg)

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 6.1 Set Hot Water Pump On Threshold

Calculate the HW\_Pump\_On\_Threshold using

HW\_Pump\_On\_Threshold = HW\_Pump\_P x HW\_Pump\_Motor\_Rated\_Current

Notes: The value of HW\_Pump\_P can be a user input or a default value.

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 6.2 Determine Hot-Water Pump Status

Update HW\_Pump\_Last\_Status

Set HW\_Pump\_Last\_Status = HW\_Pump\_Status

For each value of HW\_Pump\_Current, check if the HW\_Pump\_On\_Threshold is exceeded, and set the hot-water pump status accordingly.

If the value of HW\_Pump\_Current <= HW\_Pump\_On\_Threshold, then set HW\_Pump\_Status = "Off"

If the value of HW\_Pump\_Current > HW\_Pump\_On\_Threshold, then set HW\_Pump\_Status = "On."

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

## 7. Appendix D: Data Dictionary for Boilers

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Boiler_Capacity</td><td rowspan=1 colspan=1>The cumulative rated capacity ofall boilers used for spaceconditioning in Btu/h.</td><td rowspan=1 colspan=1>Capacity in Btu/h</td></tr><tr><td rowspan=1 colspan=1>Boiler_Cycles_Past_Hour</td><td rowspan=1 colspan=1>A variable that indicates thenumber of complete boiler on/offcycles that have occurred duringthe hour immediately precedingthe current time</td><td rowspan=1 colspan=1>Positive integer.</td></tr><tr><td rowspan=1 colspan=1>Boiler_Cycling OK/Not</td><td rowspan=1 colspan=1>Boiler cycling status variable,which can take on values asindicated in the processdescription.</td><td rowspan=1 colspan=1>Ok.&quot;Not OK. The Boiler iscycling on and offexcessively.&quot;&quot;Not OK. The Boiler iscycling on excessively.&quot;&quot;Not OK. The Boiler iscycling off excessively.&quot;</td></tr><tr><td rowspan=1 colspan=1>Boiler Fuel</td><td rowspan=1 colspan=1>A setup variable that indicates thetype of energy source used to firethe boiler.</td><td rowspan=1 colspan=1>Electric or Fossil.</td></tr><tr><td rowspan=1 colspan=1>Boiler_Last_Off_Time</td><td rowspan=1 colspan=1>A variable identifying the absolutetime at which the boiler was lastshut “Off’ (i.e., changed from on tooff).</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Boiler_Last_On_Time</td><td rowspan=1 colspan=1>A variable identifying the absolutetime at which the boiler was lastturned “On” (i.e., changed from offto on).</td><td rowspan=1 colspan=1>Time in minutes.</td></tr><tr><td rowspan=1 colspan=1>Boiler_Last_Status</td><td rowspan=1 colspan=1>The value of the Boiler Status onetime step ago (i.e., the processingtime before the current time).</td><td rowspan=1 colspan=1>&quot;On&quot; or &quot;Off”</td></tr><tr><td rowspan=1 colspan=1>Boiler_NextTo_Last_Off_Time</td><td rowspan=1 colspan=1>A variable identifying the absoluteat which the boiler was shut “Off”two times ago (i.e., changed fromon to off).</td><td rowspan=1 colspan=1>Time in minutes</td></tr><tr><td rowspan=1 colspan=1>Boiler NextTo Last On Time</td><td rowspan=1 colspan=1>A variable identifying the absolutetime at which the boiler was turned“On” two times ago (i.e., changedfrom off to on).</td><td rowspan=1 colspan=1>Time in minutes</td></tr><tr><td rowspan=1 colspan=1>Boiler_Off_Date</td><td rowspan=1 colspan=1>Numeric value for the day of theyear on which the boiler isordinarily turned off at the end ofthe heating season with the daysof the year numberedconsecutively; e.g., April 1 is day91 for a non-leap year.</td><td rowspan=1 colspan=1>Numerical value for dayof year.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Boiler_Off_Date_dDown</td><td rowspan=1 colspan=1>The number of days before theBoiler_Off_Date that the boilermay be turned off without theboiler operation considered to bein error (i.e., it should be on).</td><td rowspan=1 colspan=1>Number of days</td></tr><tr><td rowspan=1 colspan=1>Boiler_Off_Date_dUp</td><td rowspan=1 colspan=1>The number of days beyond theBoiler_Off_Date that the boilermay be on before the boileroperation is considered to be inerror (i.e., it should be off).</td><td rowspan=1 colspan=1>Number of days</td></tr><tr><td rowspan=1 colspan=1>Boiler_On_Date</td><td rowspan=1 colspan=1>Numeric value for the day of theyear on which the boiler isnormally turned on for the heatingseason with the days of the yearnumbered consecutively; e.g.,October 31 is day 304 for a non-leap year.</td><td rowspan=1 colspan=1>Numerical value for dayof year.</td></tr><tr><td rowspan=1 colspan=1>Boiler_On_Date_dDown</td><td rowspan=1 colspan=1>The number of days before theBoiler_On_Date that the boilermay be turned on without theboiler operation considered to bein error (i.e., it should be off).</td><td rowspan=1 colspan=1>Number of days</td></tr><tr><td rowspan=1 colspan=1>Boiler_On_Date_dUp</td><td rowspan=1 colspan=1>The number of days beyond theBoiler_On_Date that the boilermay be off before the boileroperation is considered to be inerror (i.e., it should be on).</td><td rowspan=1 colspan=1>Number of days</td></tr><tr><td rowspan=1 colspan=1>Boiler_On_Threshold_Electric</td><td rowspan=1 colspan=1>The electric current thresholdabove which an electric boiler isconsidered “On.&quot;</td><td rowspan=1 colspan=1>Electric current in ampsor null. Real.</td></tr><tr><td rowspan=1 colspan=1>Boiler_On_Threshold_Electric_P</td><td rowspan=1 colspan=1>Fraction of Boiler_Capaciityselected for the &quot;On&quot; Threshold forelectric boilers (e.g. 0.01)</td><td rowspan=1 colspan=1>Dimensionless realnumber between 0.0 and1.0 (e.g., 0.01)</td></tr><tr><td rowspan=1 colspan=1>Boiler_On_Threshold_Fossil</td><td rowspan=1 colspan=1>The hot water supply temperatureabove which a fossil fuel-firedboiler is considered “On.&quot;</td><td rowspan=1 colspan=1>Temperature in degreesF or null. Real.</td></tr><tr><td rowspan=1 colspan=1>Boiler_Schedule_Type</td><td rowspan=1 colspan=1>An indicator of the type of boilerschedule. It can take values of“Ambient Shutoff,” “ManualShutoff,&quot; and “Always On.&quot;</td><td rowspan=1 colspan=1>“Ambient Shutoff,”“Manual Shutoff,&quot; or&quot;Always On.&quot;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Boiler_Shutoff_OK/Not</td><td rowspan=1 colspan=1>A variable that indicates whethershut off of the boiler is controlledproperly for and consistently withthe type of boiler.</td><td rowspan=1 colspan=1>&quot;OK. The boiler is on as itshould be. Shutoff is notapplicable to this boiler.The boiler system isdesigned for continuousoperation.&quot;&quot;Not OK; the boiler is offand it should be onalways, unless it is lockedout temporarily formaintenance or repair.&quot;&quot;OK; the boiler is on as itshould be.&quot;&quot;OK; the boiler is off as itshould be&quot;&quot;Not OK; the boiler is offwhen it should be on.&quot;&quot;Not OK; the boiler is onwhen it should be off.&quot;&quot;Ok; the date is too closeto the Boiler On Date toevaluate compliance withthe schedule.&quot;&quot;Ok; the date is too closeto the Boiler Off Date toevaluate compliance withthe schedule.&quot;</td></tr><tr><td rowspan=1 colspan=1>Boiler_Stage_Power</td><td rowspan=1 colspan=1>The electric power to the boilerheating elements at the currenttime. Does not include auxiliarypower such as valves and fans.</td><td rowspan=1 colspan=1>Electric power in watts.Real.</td></tr><tr><td rowspan=1 colspan=1>Boiler_Status</td><td rowspan=1 colspan=1>A variable indicating whether theboiler is on or off.</td><td rowspan=1 colspan=1>On or Off.</td></tr><tr><td rowspan=1 colspan=1>Boiler_Status(nt * TimeStep)</td><td rowspan=1 colspan=1>Boiler_Status at the time (nt *TimeStep). The variable nt takesvalues less than or equal to zero.</td><td rowspan=1 colspan=1>On or Off.</td></tr><tr><td rowspan=1 colspan=1>BSNumber</td><td rowspan=1 colspan=1>A numerical indicator of theBoiler_Status, where Boiler_Status= “on” corresponds to BSNumber =1, and Boiler_Status = “Off&quot;corresponds to BSNumber = 0.</td><td rowspan=1 colspan=1>0 or 1</td></tr><tr><td rowspan=1 colspan=1>Current_Date</td><td rowspan=1 colspan=1>A numerical indicator of the currentdate corresponding to the currentprocessing time, counting fromJanuary 1 of each year.</td><td rowspan=1 colspan=1>Date</td></tr><tr><td rowspan=1 colspan=1>Current_Time</td><td rowspan=1 colspan=1>The absolute time of the currenttime step.</td><td rowspan=1 colspan=1>Time in minutes.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Cycle_Counts</td><td rowspan=1 colspan=1>An local variable used to keepcount of the number of completeon/off cycles during a designatedtime period.</td><td rowspan=1 colspan=1>Integer values.</td></tr><tr><td rowspan=1 colspan=1>Design_HWST</td><td rowspan=1 colspan=1>Design hot-water supplytemperature.</td><td rowspan=1 colspan=1>Temperature in degreesF. Real.</td></tr><tr><td rowspan=1 colspan=1>FHWST_High</td><td rowspan=1 colspan=1>Fraction of HWST-SP_Maintained_OK/Not equal to&quot;Too High&quot; over the lastHWST_Too_High_Window</td><td rowspan=1 colspan=1>Real value between 0.0and 1.0.</td></tr><tr><td rowspan=1 colspan=1>FHWST_High_Limit</td><td rowspan=1 colspan=1>The fraction of “Too High” hotwater supply temperatureobservations over the designatedtime window for which the long-term HWST is judged too high.</td><td rowspan=1 colspan=1>Real value between 0.0and 1.0.</td></tr><tr><td rowspan=1 colspan=1>FHWST_Low</td><td rowspan=1 colspan=1>Fraction of HWST-SP_Maintained_OK/Not equal to&quot;Too Low&quot; over the lastHWST_Too_Low_Window.</td><td rowspan=1 colspan=1>Real value between 0.0and 1.0.</td></tr><tr><td rowspan=1 colspan=1>FHWST_Low_Limit</td><td rowspan=1 colspan=1>The fraction of “Too Low” hot watersupply temperature observationsover the designated time windowfor which the long-term HWST isjudged too low.</td><td rowspan=1 colspan=1>Real value between 0.0and 1.0.</td></tr><tr><td rowspan=1 colspan=1>HW_Pump_Current</td><td rowspan=1 colspan=1>The measured value of current forthe hot-water pump</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>HW_Pump_On_Threshold</td><td rowspan=1 colspan=1>The value of hot-water pumpcurrent (HW_Pump_Current)above which the pump isconsidered on.</td><td rowspan=1 colspan=1>Current in amps.</td></tr><tr><td rowspan=1 colspan=1>HW_Pump_Last_Status</td><td rowspan=1 colspan=1>The value of theHW_Pump_Status one time stepago (i.e., the processing timebefore the current time).</td><td rowspan=1 colspan=1>&quot;On&quot; or &quot;Off”</td></tr><tr><td rowspan=1 colspan=1>HW_Pump_Motor_Rated_Current</td><td rowspan=1 colspan=1>Current rating of the hot-waterpump motor from the motornameplate.</td><td rowspan=1 colspan=1>Current in amps</td></tr><tr><td rowspan=1 colspan=1>HW_Pump_P</td><td rowspan=1 colspan=1>Fraction of Hot-Water pump ratedcurrent selected for the &quot;On&quot;Threshold.</td><td rowspan=1 colspan=1>Dimensionless realnumber between 0.0 and1.0.</td></tr><tr><td rowspan=1 colspan=1>HW_Pump_Run_Limit</td><td rowspan=1 colspan=1>The maximum time interval afterthe boiler turns off during which thehot-water pump can run. After thistime, the hot-water pump shouldnot turn on again until the boilerturns on.</td><td rowspan=1 colspan=1>Time interval in hours.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>HW_Pump_Shutoff_OK/Not</td><td rowspan=1 colspan=1>A variable indicator whether theOn/Off status of the hot-waterpump is being controlled properlyor not, and if not, how is it&#x27;s controlwrong.</td><td rowspan=1 colspan=1>&quot;OK; the hot-water pumpis off as it should be.&quot;&quot;OK; the hot water pumpis on while the boiler ison.&quot;&quot;Hot Water PumpingFault; the pump is off toomuch while the boiler ison.&quot;&quot;HW Pump is runningunnecessarily andwasting energy anduseful operating life.&quot;&quot;OK; the hot-water pumpis running while the boileris off, but the hot-waterrun limit has not beenexceeded yet.&quot;</td></tr><tr><td rowspan=1 colspan=1>HW_Pump_Status</td><td rowspan=1 colspan=1>A variable indicating whether thehot-water pump is on or off.</td><td rowspan=1 colspan=1>&quot;On” or &quot;Off”</td></tr><tr><td rowspan=1 colspan=1>HWST</td><td rowspan=1 colspan=1>Hot-water supply temperature</td><td rowspan=1 colspan=1>Temperature in degreesF.</td></tr><tr><td rowspan=1 colspan=1>HWST_dDown</td><td rowspan=1 colspan=1>Maximum acceptable deviation ofthe hot-water supply temperaturebelow its set point for a singlemeasurement.</td><td rowspan=1 colspan=1>Temperature in degreesF.</td></tr><tr><td rowspan=1 colspan=1>HWST_Deviation</td><td rowspan=1 colspan=1>The hot water supply temperaturedeviation from set point for thecurrent observation. [Note: Thisoutput is included only forconsistency with the chilled waterreset diagnostic and may not beneeded.]</td><td rowspan=1 colspan=1>Temperature difference indegrees F.</td></tr><tr><td rowspan=1 colspan=1>HWST_dUp</td><td rowspan=1 colspan=1>Maximum acceptable deviation ofthe hot-water supply temperatureabove its setpoint for a singlemeasurement.</td><td rowspan=1 colspan=1>Temperature in degreesF.</td></tr><tr><td rowspan=1 colspan=1>HWST_Maintained_OK/Not</td><td rowspan=1 colspan=1>Hot Water Supply TemperatureStatus Message. Possible values:“OK,&quot;“Too high,&quot;“Too Low.&quot;</td><td rowspan=1 colspan=1>Ok.Too high.Too low.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>HWST_Maintained_OK/not_Too-Low_Ārray</td><td rowspan=1 colspan=1>The array:{HWST_Maintained_OK/not,HWST_Maintained_OK/not (1 timestep ago), HWST_MaintainedOK/not (2 time steps ago),HWSTMaintained_OK/not (3 timesteps ago), HWST_Maintained-OK/not (4 time steps ago),...HWST Maintained OK/not[(HWST_Too_Low_Window - 1)time steps ago]}</td><td rowspan=1 colspan=1>Array with individualelements takings valuesof Ok, Too High, or TooLow.</td></tr><tr><td rowspan=1 colspan=1>HWST_Maintained_OK/not_Too-High_Array</td><td rowspan=1 colspan=1>The array:{HWST_Maintained_OK/not,HWST_Maintained_OK/not (1 timestep ago), HWST_MaintainedOK/not (2 time steps ago),HWSTMaintained_OK/not (3 timesteps ago), HWST_Maintained-OK/not (4 time steps ago),.HWST_Maintained_OK/not[(HWST_Too_High_Window - 1)time steps ago]}</td><td rowspan=1 colspan=1>Array with individualelements takings valuesof Ok, Too High, or TooLow.</td></tr><tr><td rowspan=1 colspan=1>HWSTNumber_High</td><td rowspan=1 colspan=1>HWSTNumber High is the numberof values of the variableHWST_Maintained_OK/not withvalues of “Too High” during the lastHWST_Too_High_Window timesteps.</td><td rowspan=1 colspan=1>Integer.</td></tr><tr><td rowspan=1 colspan=1>HWSTNumber_Low</td><td rowspan=1 colspan=1>HWSTNumber Low is the numberof values of the variableHWST_Maintained_OK/not withvalues of “Too Low” during the lastHWST_Too_Low_Window timesteps.</td><td rowspan=1 colspan=1>Integer.</td></tr><tr><td rowspan=1 colspan=1>HWST_Setpoint-Current</td><td rowspan=1 colspan=1>Hot-water supply temperaturesetpoint for the current time.</td><td rowspan=1 colspan=1>Temperature in degreesF.</td></tr><tr><td rowspan=1 colspan=1>HWST-SP Maintained OK/Not</td><td rowspan=1 colspan=1>An indicator of whether the hot-water supply temperature isadequately maintained at a singlepoint in time.</td><td rowspan=1 colspan=1>OKToo highToo low</td></tr><tr><td rowspan=1 colspan=1>HWST_Too_High_Window</td><td rowspan=1 colspan=1>Length in number of observationsof the moving time window overwhich the percentage of too highhot water supply temperatures isevaluated.</td><td rowspan=1 colspan=1>Number of time steps.Integer</td></tr><tr><td rowspan=1 colspan=1>HWST_Too_Low_Window</td><td rowspan=1 colspan=1>Length in number of observationsof the moving time window overwhich the percentage of too lowhot water supply temperatures isevaluated.</td><td rowspan=1 colspan=1>Number of time steps.Integer</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Automated Diagnostics</td><td rowspan=1 colspan=1>Version:      1.1</td></tr><tr><td rowspan=1 colspan=1>Software Requirements Specification</td><td rowspan=1 colspan=1>Date: 8/28/2003</td></tr><tr><td rowspan=1 colspan=2>&lt;document identifier&gt;</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Variable</td><td rowspan=1 colspan=1>Definition</td><td rowspan=1 colspan=1>Values</td></tr><tr><td rowspan=1 colspan=1>Latest_Complete_Boiler_Off_Duration</td><td rowspan=1 colspan=1>The length of time over which theboiler was off the last time it wentthrough a complete off-cycle (i.e.,from on to off to on again).</td><td rowspan=1 colspan=1>Time interval in minutes.</td></tr><tr><td rowspan=1 colspan=1>Latest_Complete_Boiler_On_Duration</td><td rowspan=1 colspan=1>The length of time over which theboiler was on the last time it wentthrough a complete on-cycle (i.e.,from off to on to off again).</td><td rowspan=1 colspan=1>Time interval in minutes.</td></tr><tr><td rowspan=1 colspan=1>Max_Normal_Boiler_CPH</td><td rowspan=1 colspan=1>A setup variable for the maximumnumber of cycles that the boilershould go through in an hour.</td><td rowspan=1 colspan=1>Positive integer.</td></tr><tr><td rowspan=1 colspan=1>Min_Normal_Boiler_Off_Duration</td><td rowspan=1 colspan=1>A setup variable that indicates theminimum time the boiler should beoff before turning on again.</td><td rowspan=1 colspan=1>Time interval in minutes.</td></tr><tr><td rowspan=1 colspan=1>Min_Normal_Boiler_On_Duration</td><td rowspan=1 colspan=1>A setup variable that indicates theminimum time the boiler should beon before shutting offagain.</td><td rowspan=1 colspan=1>Time interval in minutes.</td></tr><tr><td rowspan=1 colspan=1>Nmax</td><td rowspan=1 colspan=1>Number of times steps per hour =60/TimeStep = the roundednumber of calculation time stepsper hour given the length of thetime step designated during set up.</td><td rowspan=1 colspan=1>Positive integer.</td></tr><tr><td rowspan=1 colspan=1>nt</td><td rowspan=1 colspan=1>An index for the number of timesteps.</td><td rowspan=1 colspan=1>Integer, usually less thanor equal to zero.</td></tr><tr><td rowspan=1 colspan=1>TimeStep</td><td rowspan=1 colspan=1>A setup variable for the length oftime between successiveprocessings in minutes (which isassumed constant).</td><td rowspan=1 colspan=1>Time increment inminutes.</td></tr><tr><td rowspan=1 colspan=1>Time_Steps_Processed</td><td rowspan=1 colspan=1>Total number of time stepsprocessed since the beginning ofprocessing.</td><td rowspan=1 colspan=1>Integer.</td></tr></table>