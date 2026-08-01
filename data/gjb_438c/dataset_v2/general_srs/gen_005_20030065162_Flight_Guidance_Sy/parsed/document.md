![](images/c41b169a7bd4a59c3f87e67f8da2e49600b53cb52beeac4d34aa287551a5db43.jpg)

# Flight Guidance System Requirements Specification

Steven P. Miller, Alan C. Tribble, Timothy M. Carlson, and Eric J. Danielson Rockwell Collins, Cedar Rapids, Iowa

Since its founding, NASA has been dedicated to the advancement of aeronautics and space science. The NASA Scientific and Technical Information (STI) Program Office plays a key part in helping NASA maintain this important role.

The NASA STI Program Office is operated by Langley Research Center, the lead center for NASA's scientific and technical information. The NASA STI Program Office provides access to the NASA STI Database, the largest collection ofaeronautical and space science STI in the world. The Program Office is also NASA's institutional mechanism for disseminating the results of its research and development activities. These results are published by NASA in the NASA STI Report Series, which includes the following report types:

TECHNICAL PUBLICATION. Reports of completed research or a major significant phase of research that present the results of NASA programs and include extensive data or theoretical analysis. Includes compilations of significant scientific and technical data and information deemed to be of continuing reference value. NASA counterpart of peerreviewed formal professional papers, but having less stringent limitations on manuscript length and extent of graphic presentations.

TECHNICAL MEMORANDUM. Scientific and technical findings that are preliminary or of specialized interest, e.g., quick release reports, working papers, and bibliographies that contain minimal annotation. Does not contain extensive analysis.

CONTRACTOR REPORT. Scientific and technical findings by NASA-sponsored contractors and grantees.

CONFERENCE PUBLICATION. Collected papers from scientific and technical conferences, symposia, seminars, or other meetings sponsored or co-sponsored by NASA.

SPECIAL PUBLICATION. Scientific. technical, or historical information from NASA programs, projects, and missions, often concerned with subjects having substantial public interest.

TECHNICAL TRANSLATION. Englishlanguage translations of foreign scientific and technical material pertinent to NASA's mission.

Specialized services that complement the STI Program Office's diverse offerings include creating custom thesauri, building customized databases, organizing and publishing research results ... even providing videos.

For more information about the NASA STI Program Office, see the following:

• Access the NASA STI Program Home Page at http://www.sti.nasa.gov

• E-mail your question via the Internet to help@sti.nasa.gov

Fax your question to the NASA STI Help Desk at (301) 621-0134

Phone the NASA STI Help Desk at (301) 621-0390

Write to:   
NASA STI Help Desk   
NASA Center for AeroSpace Information   
7121Standard Drive   
Hanover, MD 21076-1320

![](images/e3f64c82a2bd5ff3c4b1a0ffc37bd192d6669039509828fa0ad38d602a8949d3.jpg)

# Flight Guidance System Requirements Specification

Steven P. Miller, Alan C. Tribble, Timothy M. Carlson, and Eric J. Danielson Rockwell Collins, Cedar Rapids, Iowa

National Aeronautics and Space Administration

Available from:

## Abstract

This report describes a requirements specification written in the $\mathrm { R S M L } ^ { - e }$ language for the mode logic of a Flight Guidance System of a typical regional jet aircraft. This model was created as one of the first steps in five-year project sponsored by the NASA Langley Research Center, Rockwell Collins Inc., and the Critical Systems Research Group of the University of Minnesota to develop new methods and tools to improve the safety of avionics designs. This model will be used to demonstrate the application of a variety of methods and techniques, including safety analysis of system and subystem requirements, verification of key properties using theorem provers and model checkers, identification of potential sources mode confusion in system designs, partitioning of applications based on the criticality of system hazards, and autogeneration of avionics quality code. While this model is representative of the mode logic of a typical regional jet aircraft, it does not describe an actual or planned product. Several aspects of a full Flight Guidance System, such as recovery from failed sensors, have been omitted, and no claims are made regarding the accuracy or completeness of this specification.

## Contents

1 Introduction 5   
1.1 How Requirements Analysis Relates to Aircraft Safety 5   
1.2 Overview of a Flight Guidance System 9   
1.3 Fundamentals of the Mode Logic 12   
2 The FGS Requirements Specification 15   
2.1 Overview of the FGS Specification 16   
2.2 Prioritization of Events 20   
2.3 Basic Definitions 23   
2.4 Flight Director (FD) 25   
2.5 Pilot Flying (PF) 29   
2.6 Independent Mode 30   
2.7 Flight Modes 32   
2.7.1 Lateral Modes 35   
2.7.1.1 Roll Hold (ROLL) Mode 37   
2.7.1.2 Heading Select (HDG) Mode 40   
2.7.1.3 Navigation (NAV) Mode 44   
2.7.1.4 Lateral Approach (LAPPR) Mode 50   
2.7.1.5 Lateral Go Around (LGA) Mode 56   
2.7.2 Vertical Modes 60   
2.7.2.1 Pitch Hold (PITCH) Mode 62   
2.7.2.2 Vertical Speed (VS) Mode 65   
2.7.2.3 Flight Level Change (FLC) Mode 69   
2.7.2.4 Altitude Hold (ALT) Mode 73   
2.7.2.5 Altitude Select (ALTSEL) Mode 77   
2.7.2.6 Vertical Approach (VAPPR) Mode . 85   
2.7.2.7 Vertical Go Around (VGA) Mode 91   
2.8 Flight Control Laws 95   
2.9 Flight Control Panel (FCP) 103   
2.10 Navigation Sources 127   
2.11 Air Data System 128   
2.12 References 129   
2.13 Autopilot (AP) . 130   
2.14 Offside FGS .133   
2.15 FGS Inputs .152   
2.16 FGS Outputs . 156   
References . .161   
Index .163

## Chapter 1

## Introduction

This report describes a requirements specification written in the RSML-e [8, 6] language for the mode logic of a Flight Guidance System of a typical regional jet aircraft. This model was created as one of the first steps in a project sponsored by the NASA Langley Research Center, Rockwell Collins, Inc., and the Critical Systems Research Group of the University of Minnesota to develop new methods and tools to improve the safety of avionics designs. This model will be used to demonstrate the application of a variety of methods and techniques, including:

• Safety analysis of system and subsystem requirements

• Verification of key properties using theorem provers and model checkers

• Identification of potential sources mode confusion in system designs

• Partitioning of applications based on the criticality of system hazards

• Autogeneration of avionics quality code

While this model is representative of the mode logic of a typical regional jet aircraft, it does not describe an actual or planned product. Several aspects of a full Flight Guidance System, such as recovery from failed sensors, have been omitted, and no claims are made regarding the accuracy or completeness of this specification

The report is organized as follows. In this chapter, Section 1.1 discusses why the modeling and analysis of requirements is important to aircraft safety, Section 1.2 provides an overview of a modern Flight Guidance System, and Section 1.3 discusses the the fundamentals of the mode logic found in the FGS. Chapter 2 deals with the requirements specification itself. Section 2.1 describes how the specification is organized. The remaining sections of Chapter 2 are the specification itself.

## 1.1 How Requirements Analysis Relates to Aircraft Safety

Aircraft safety has improved steadily over the last few decades and much of this improvement can be attributed to the introduction of advanced automation in the cockpit. The predicted ten-fold increase in air traffic by 2016 will force much greater reliance on automated systems. New technologies, such as: Communication, Navigation, and Surveillance for Air Traffic Management (CNS/ATM); Global Air Traffic Management (GATM); Global Positioning System (GPS); and fly-by-wire, will be introduced to meet enhanced safety and performance goals. Table 1.1 classifies the fatal accidents of the worldwide commercial jet fleet for the period of 1990 to 1999. Categories in which automated systems can play a role in reducing the accident rate still further are emphasized. These account for almost 80 percent of the accidents and fatalities.

<table><tr><td rowspan=1 colspan=1>Accident Category</td><td rowspan=1 colspan=1>Fatalities</td><td rowspan=1 colspan=1>Accidents</td></tr><tr><td rowspan=1 colspan=1>Controlled Flight Into Terrain</td><td rowspan=1 colspan=1>2111</td><td rowspan=1 colspan=1>28</td></tr><tr><td rowspan=1 colspan=1>Loss of Control in Flight</td><td rowspan=1 colspan=1>2011</td><td rowspan=1 colspan=1>29</td></tr><tr><td rowspan=1 colspan=1>In Flight Fire</td><td rowspan=1 colspan=1>600</td><td rowspan=1 colspan=1>3</td></tr><tr><td rowspan=1 colspan=1>Midair Collision</td><td rowspan=1 colspan=1>506</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=1>Fuel Tank Explosion</td><td rowspan=1 colspan=1>238</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=1>Landing</td><td rowspan=1 colspan=1>~200</td><td rowspan=1 colspan=1>14</td></tr><tr><td rowspan=1 colspan=1>Takeoff</td><td rowspan=1 colspan=1>~144</td><td rowspan=1 colspan=1>3</td></tr><tr><td rowspan=1 colspan=1>Ice/Snow</td><td rowspan=1 colspan=1>~60</td><td rowspan=1 colspan=1>3</td></tr><tr><td rowspan=1 colspan=1>Fuel Exhaustion</td><td rowspan=1 colspan=1>~40</td><td rowspan=1 colspan=1>5</td></tr><tr><td rowspan=1 colspan=1>Wind Shear</td><td rowspan=1 colspan=1>~30</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=1>Runway Incursion</td><td rowspan=1 colspan=1>~10</td><td rowspan=1 colspan=1>4</td></tr><tr><td rowspan=1 colspan=1>Misc. Fatality</td><td rowspan=1 colspan=1>~10</td><td rowspan=1 colspan=1>3</td></tr><tr><td rowspan=1 colspan=1>On Ground</td><td rowspan=1 colspan=1>~10</td><td rowspan=1 colspan=1>3</td></tr><tr><td rowspan=1 colspan=1>Refused Takeoff</td><td rowspan=1 colspan=1>~10</td><td rowspan=1 colspan=1>1</td></tr><tr><td rowspan=1 colspan=1>Turbulence</td><td rowspan=1 colspan=1>~10</td><td rowspan=1 colspan=1>3</td></tr><tr><td rowspan=1 colspan=1>Unknown</td><td rowspan=1 colspan=1>482</td><td rowspan=1 colspan=1>7</td></tr><tr><td rowspan=1 colspan=1>Total</td><td rowspan=1 colspan=1>6465</td><td rowspan=1 colspan=1>112</td></tr></table>

Table 1.1: Fatal Accidents - Worldwide Commercial Jet Fleet, 1990-1999 - From [14]

However, the growing complexity and integration issues associated with these advanced technologies also increase the potential for errors that could have a direct impact on safety. As systems become more tightly integrated, even the engineers that design them will find it difficult to anticipate every possible interaction. Unfortunately, it is precisely these interactions that will have the greatest impact on safety:

Today more accidents result from dangerous design characteristics and interactions among components.[10]

Complex and highly integrated avionics present greater risk for development error. With non-traditional human-machine interfaces, there is also the potential for operational flight crew errors. Moreover, integration of systems may result in a greater likelihood of undesirable and unintended effects.[2]

In spite of the increased safety concerns, manufacturers are being asked to design, develop and validate the systems of the future under the budgets of the past. It is imperative that new methods to improve system safety be developed, and that these methods work in concert with the goals of reducing cost and cycle time.

One of the best ways to improve product quality while reducing costs is to develop a complete, consistent, and well organized set of requirement at the start of the product life cycle. As stated by Fred Brooks:

The hardest single part of building a software system is deciding precisely what to build. No other part of the conceptual work is as difficult as establishing the detailed technical requirements... No other part of the work so cripples the resulting system if done wrong. No other part is as difficult to rectify later.[4]

The majority of software development errors stem from logic errors made during requirements analysis. Most of these errors are not found until the later phases of a project. The amount of rework that has to be done to fix a requirements error, and the cost of doing so, grows dramatically the later it is detected.[1] In one well-known study, it was found that it costs ten times as much to correct a requirements error during unit testing as during requirements analysis. Correcting a requirements error after a product had been deployed increased the cost by 100 to 200 times.[3] Moreover, requirements errors are often the most serious errors. Investigators focusing on safetycritical systems have found that requirements errors are more likely to affect the safety of an embedded system than errors introduced during design or implementation.[12]

One of the most successful approaches to finding requirements errors is to create a precise model of the system's externally visible behavior that can be executed. Several notations have been developed over the last few years for creating a model of the system's functional behavior that is both readable and mathematically precise. Among the better known are SCR [7], RSML [8, 6], SpecTRM [10], and Statecharts [5]. Creating models based on these notations have been shown to find a wealth of errors in textual specifications [6, 13]. Moreover, such models can be connected to a mock-up of the user interface and executed with the customer in the same way as a simulation. In the best approaches, the underlying notation has been carefully designed to support automated analyses. These make possible a variety of consistency and completeness checks that find many errors, as well as the ability to check for properties specific to the application being modeled. Finally, the requirements model itself becomes a detailed statement of the desired behavior. This enhances design and testing, and makes it far more feasible to outsource the software development.

In short, creation of a precise model of a system's behavior not only finds errors early in the life-cycle when they can be most economically addressed, it enables a variety of downstream activities tradionally associated with the quality of the system, including design, coding, and verification. Particularly relevant to this report, it lays the foundation for improving system safety through analysis:

Every hazard analysis requires some type of model of the system, which may range from a fuzzy idea in the analyst's mind to a complex and carefully specified mathematical model. The model may range from a high-level abstraction to a low-level and detailed prototype. Nevertheless, information about the system must exist in some form, and that constitutes the system model upon which the analysis is performed.[11]

The model of a Flight GuidanceSystem described in this report will be used for the demonstration of a wide variety of techniques developed to improve the quality and safety of embedded systems, thereby reducing the accident rate shown in Table 1.1.

## 1.2 Overview of a Flight Guidance System

A Flight Guidance System (FGS) is a component of the overall Flight Control System (FCS). It compares the measured state of an aircraft (position, speed, and attitude) to the desired state and generates pitch and roll guidance commands to minimize the difference between the measured and desired state. A simplified overview of an FCS that emphasizes the role of the FGS is shown in Figure 1.1.

![](images/e829e180786db152db91fdc5b915d9ab55662ae0eee5e1f3646c4cbd2598f7de.jpg)  
Figure 1.1: Flight Control System Overview

As shown in Figure 1.1, the FGS subsystem accepts input about the aircraft's state from the Attitude Heading Reference System (AHRS), Air Data System (ADS), Flight Management System (FMS), and Navigation Radios. Using this information, it computes pitch and roll guidance commands that are provided to the Autopilot (AP). When engaged, the Autopilot translates these commands into movement of the aircraft's control surfaces necessary to achieve the commanded changes about the lateral and vertical axes.

The flight crew interacts with the FGS primarily through the Flight Control Panel (FCP), shown in more detail in Figure 1.2. The FCP includes switches for turning the Flight Director (FD) on and off, switches for selecting the different flight modes such as vertical speed (VS), lateral navigation (NAV), heading select (HDG), altitude hold (ALT), and approach (APPR), the Vertical Speed/Pitch Wheel, and the autopilot disconnect bar. The FCP also supplies feedback to the crew, indicating selected modes by lighting lamps on either side of a selected mode's button. Figure 1.2 depicts a configuration in which Heading Select (HDG) mode is selected.

![](images/e895ec3a3c0e77f7fb43ca82e119fe2bbb2d22641542cb694200f6eaa00d4c01.jpg)  
Figure 1.2: Flight Control Panel

A few key controls, such as the Go Around button and the Autopilot Disengage switch, are provided on the control yokes and throttles and routed through the FCP to the FGS. Navigation sources are selected through the Display Control Panel (DCP), with the selected navigation source routed through the PFD to the FGS.

The FGS has two physical sides, or channels, one on the left side and one on the right side of the aircraft (see Figure 1.1). These provide redundant implementations that communicate with each other over a cross-channel bus. Each channel of the FGS can be further broken down into the mode logic and the flight control laws. The flight control laws accept information about the aircraft's current and desired state and compute the pitch and roll guidance commands. The mode logic determines which lateral and vertical modes of operation are active and armed at any given time. These in turn determine which flight control laws are active and armed. These are annunciated, or displayed, on the Primary Flight Displays (PFD) along with a graphical depiction of the flight guidance commands generated by the FGS.

A simplified image of a Primary Flight Display (PFD) is shown in Figure 1.3. The PFDs display essential information about the aircraft, such as airspeed, vertical speed, attitude, the horizon, and heading. The active lateral and vertical modes are displayed (annunciated) at the top of the display. The annunciations in Figure 1.3 indicate that the current active lateral mode is Heading Select (HDG), the active vertical mode is Pitch (PTCH), and that Altitude Select (ALTS) mode is armed.

The large sphere in the center of the PFD is the sky/groundball. The horizontal line across its middle is the artificial horizon. The current pitch and roll of the aircraft is indicated by a white wedge ∧ representing the aircraft in the middle of the sky/ground ball. Figure 1.3 depicts an aircraft with zero degrees of roll and pitched up approximately five degrees.

The graphical presentation of the pitch and roll guidance commands on the PFD are referred to as the Flight Director (FD). 1 The pitch and roll guidance commands are shown as a magneta wedge ∧ in the sky/ground ball. When the autopilot is not engaged, these are interpreted as guidance to the pilot. When the autopilot is engaged, these indicate the direction the aircraft is being steered by the autopilot. Figure 1.3 depicts an aircraft in which the autopilot is not engaged and the Flight Director is commanding the pilot to pitch up and roll to the right.

![](images/984a3a75bfd0de8d6fd8614ec53859cc7427dcac3d17e31c8c1544aa5c3d1b68.jpg)  
Figure 1.3: Primary Flight Display

## 1.3 Fundamentals of the Mode Logic

A mode is defined by Leveson as a “mutually exclusive set of system behaviors" [9]. Specifically as it relates to an FGS, advisory circular AC/ACJ 25.1329 defines a mode as “a system configuration that corresponds to a single (or set of) FGS behavior(s)" [2]. The primary modes of interest in an FGS are the lateral and vertical modes. The lateral modes control the behavior of the aircraft about the longitudinal, or roll, axis, while the vertical modes control the behavior of the aircraft about the vertical, or pitch, axis. In addition, there are a number of auxillary modes, such as half-bank mode, that control other aspects of the aircraft's behavior. Examples of FGS modes include Heading Hold (HDG) which holds the aircraft to a selected heading and Vertical Speed (VS) mode which holds the aircraft to selected vertical speed.

A mode is said to be selected if it has been manually requested by the flight crew or if it has been automatically requested by a subsystem such as the FMS. The simplest modes have only two states, cleared and selected, as shown in Figure 1.4. Such a mode becomes active immediately upon selection with it's associated flight control law providing guidance commands to the flight director and, if engaged, the autopilot. When cleared, a mode's associated flight control law is non-operational, i.e., it does not generate any outputs.

![](images/8b8853f572ebca3cfb33d1d31af3fedc808c528f792845db940a01791527df05.jpg)  
Figure 1.4: ASimple Mode

Some modes can be armed to become active when a criterion is met, such as the acquisition of a navigation source or proximity to a target reference such as a desired altitude. Such modes have three states as shown in Figure 1.5. The two states armed and active are substates of the selected state, i.e., when the mode is armed or active, it is also said to be selected. While in the armed state, the mode's flight control law is not generating guidance commands for the flight director or the autopilot, but it may be accepting inputs, accumulating state information, and helping to determine if the criterion for becoming active is met. Once the criterion is met, the mode transitions to the active state and its flight control law begins generating guidance for the flight director and autopilot. Note that the only way to exit the active state is to deselect the mode, i.e., it is not usually possible to revert directly from the active state to the armed state.

![](images/f49001869be6daa3f6e3fbe8ef48703553c69e5300a2b38194c757a483b7a7ea.jpg)  
Figure 1.5: A Mode with Armed and Active Substates

Some modes also distinguish between capturing and tracking of the target reference or navigation source. Such a mode is shown in Figure 1.6. Once in the active state, such a mode's flight control law first captures the target by manuvering the aircraft to align it with the navigation source or reference. Once correctly aligned, the mode transitions to the tracking state in which it holds the aircraft on the target. Both the capture and track states are substates of the active state and the mode's flight control law is active in both states, i.e., generating guidance commands for the flight director and autopilot. Note that the only way to exit the active, track, or capture states is to deselect the mode, i.e., it is not possible to revert directly from the track state to the capture state or from the active state to the armed state.

![](images/060d5836f73a91550112f1d2a692d47b8464eab8cf7a264880c66f11a742973e.jpg)  
Figure 1.6: A Mode with Capture and Track Substates

The mode logic consists of all the available modes and the rules for transitioning between them. Figure 1.7 provides an overview of the modes described in this specification. Traditionally, aircraft modes are associated with a flight control law that determines the guidance provided to the flight director or autopilot. For example, in Figure 1.7, there are lateral modes of Roll Hold, Heading Hold, Navigation, Lateral Approach, and Lateral Go Around. These control the guidance about the longitudinal, or roll, axis. Guidance about the vertical, or pitch, axis is controlled by the vertical modes of Pitch, Vertical Speed, Altitude Hold, Altitude Select, Vertical Approach, and Vertical Go Around. Each of these are associated with one or more control laws.

Also shown in Figure 1.7 are several auxillary modes such as Pilot Flying, Independent Mode, FD, and AP, that describe the status of key state variables. While these have an important affect upon the behavior of the aircraft, they are not directly associated with specific flight control laws, and are not usually viewed as “modes" by system designers in the same way the lateral and vertical modes are.

In order to provide effective guidance of the aircraft, these modes are tightly synchronized so that only a small portion of their total state space is actually reachable. For example, to ensure that meaningful guidance is provided to the flight director and autopilot, only one lateral and one vertical mode can be active at any time. For the same reason, if the autopilot is engaged or the flight director is turned on, at least one lateral and one vertical mode must be active. Other constraints enforce sequencing of modes that are dictated by the characteristics of the aircraft and the airspace. For example, vertical approach mode is not usually allowed to become active until lateral approach mode has become active to ensure that the aircraft is horizontally centered on the localizer before tracking the glideslope. These constraints are clearly important to safe flight, and can become quite complex. The mode logic is responsible for enforcing all these constraints.

![](images/604d9c74dad7718ac327977e735b5c3274bbbb2f45938bb84d6ea5f04f04bc8a.jpg)  
Figure 1.7: FGS Mode Logic

## Chapter 2

# The FGS Requirements Specification

A requirements specification must meet the needs of a diverse set of stakeholders, including but not limited to the customer, end users, program management, systems engineers, software engineers, hardware engineers, test engineers, and regulatory agencies. It must be clear enough that end users can understand it, yet complete and precise enough that the engineers can implement the system correctly and develop a comprehensive set of test cases. It must be robust in the face of change so that small changes only require small efforts. Ideally, the specification should support the development of a family of products, so that it can easily be reused to develop an entire line of similar products.

The FGS requirements specification described in this document is organized to meet these goals. Its structure is hierarchial, allowing the reader to start with the entire subsystem, then examine individual components in greater detail. To enhance readability, it makes heavy use of the tabular formats developed in $\mathrm { R S M L } ^ { - e }$ to make the complex logic of the Traffic Collision Avoidance System (TCAS) accessible to pilots, engineers, and regulatory authorities. [6]

Some of these goals, particularly those related to robustness in the face of change and support for product families, are best achieved by organizing the specification into pieces that are logically related and likely to change together and by defining interfaces between these components that are unlikely to change. The current version of RSML-e does not directly support these notions, though extensions are planned for future versions that will.

However, this specification has been written as though these features were available. Functions that are logically related are grouped together into components, with details that are likely to change encapsulated within these components. Rather than referring to these directly in the other parts of the specification, interfaces (e.g., functions or macros) are defined that should remain stable over time for use in the rest of the specification. Many of the architectural decisions are based on an extensive commonality analysis of several Flight Guidance Systems to determine which features change and which remain stable over a periodof time. To facilitate such anticipated changes, the architecture implicitly defines a framework in which common patterns and interfaces are used across similar components.

![](images/50233cf06cd3e39c8c226375de0e695a527e2d3474acdcb5f9e9aed929564932.jpg)  
Figure 2.1: Flight Guidance Specification Overview

## 2.1 Overview of the FGS Specification

The top level structure of the FGS is shown in Figure 2.1. The enclosing box labeled Flight Guidance System represents the full specification. The components located on the edge of the FlightGuidance System are boundary components that define the system's view of its interfaces with the outside world. These do not define the behavior of the actual external subsystem. Rather, they define the behavior of that subsystem that the FGS must be aware of. For example, the component labeled Flight Control Panel (FCP) only defines what information is received by and sent to the Flight Control Panel and does not define the full behavior of that actual device.

Each component may define new events or values that are used by other components. For example, the FCP mentioned above defines and exports events for each switch that can be pressed on the panel. In fact, since several of these events can occur at the same time, the FCP component defines a prioritization of these events so that only the highest priority events are seen by the rest of the specification (see Section 2.2).

The heart of the specification is the definition of the mode logic contained in the Modes component. This is further broken down into the Lateral Modes and Vertical Modes, which are in turn broken down into individual modes. The lateral and vertical modes all present standard interfaces to their parent modules, making it staightforward to add, remove, or substitute modes, a common source ofvariation in a FGS. In addition, many of the modes share a common behavior that can be specified once, then tailored to define the behavior of each individual mode.

The following sections provide an overview of each individual component. Detailed specifications of the components can be found in the remainder of this chapter.

Flight Control Panel (page 103) The Flight Control Panel (FCP) is the primary device with which the flight crew interacts with the FGS. This component defines the FGS's view of the FCP. This consists of the definition of the monitored variables representing the switches and dials of the FCP and the controlled variables representing the lamps displayed on the FCP. A few additional inputs, such as the SYNC and AP Disengage switches on the control yokes and the GA switches on the throttles, are routed through the FCP aand are defined here. This component also defines FCP specific events, such as the pressing of a switch. used in the rest of the specification. These events are prioritized so that if multiple events occur at the same time, only the most significant events are seen by the other parts of the specification.

Flight Director (page 25) The Flight Director (FD) displays the pitch and roll guidance commands to the pilot and copilot on the Primary Flight Display. This component defines when the Flight Director guidance cues are turned on and off.

Independent Mode (page 30) Normally, the FGS operates in dependent mode in which the pilot flying (PF) side of the FGS provides the mode annunciations and FD guidance commands to both PFDs. While in dependent mode, the pilot not flying (PNF) side of the FGS synchronizes its modes to the pilot flying side. Under final approach conditions and during takeoff or go around modes, the FGS operates in independent mode in which each side operates independently of the other side and provides mode annunciations and FD guidance commands to its own PFD. This component defines when the FGS enters independent mode.

Pilot Flying (page 29) The transfer switch on the FCP is used to determine which FGS provides mode annunciations and guidance commands to the PFDs while in dependent mode. This component defines which side is the Pilot Flying side. It also defines the notion of the “active" side of the FGS. A side of the FGS is said to be “active" if it is providing mode annunciations and guidance commands to its PFD.

Flight Control Laws (page 95) The Flight Control Laws generate the pitch and roll guidance commands provided to the Flight Director and the Autopilot. Different Flight Control Laws are armed or activated based on the current modes of the FGS. They also provide inputs to the mode logic that determine when transitions are made from the armed to the active state. While the Flight Control Laws are not specified in this model, this component defines the interface between them and the mode logic and defines the events provided by the Flight Control Laws that the mode logic depends upon. As with events provided by the Flight Control Panel, some of these are prioritized so that if multiple events occur at the same time, only the most significant events are seen by the other parts of the specification.

Navigation Sources (page 127) The FGS receives navigation information from several sources including VHF Omni-Directional Range (VOR) for lateral navigation, Localizer (LOC) for precision lateral approach, and Glideslope (GS) for precision vertical approach. This component defines the FGS's view of its navigation sources. This includes definition of the types of sources available, the currently selected source, and the information available from that source.

Air Data System (page 128) The Air Data System provides information about the aircraft state sensed from the surrounding air mass such as pressure altitude and indicated airspeed. This component defines the FGS's view of the Air Data System.

## References (page 129)

References refer to target values used by several of the modes, such as the Preselected Altitude. These may be set by the flight crew through the Flight Control Panel, or set to the current aircraft value on entry to a mode or a synchronization request. The references may be physically maintained by a variety of systems. This component defines the FGS's view of the references. Details of how these values are obtained from other systems are encapsulated within this component.

Autopilot (page 130) The Autopilot (AP) commands the movement the control surfaces based on the pitch and roll commands generated by the FGS. This component defines the FGS's view of the AP.

Offside FGS (page 133) The FGS has two physical sides, or channels, on the left and right sides of the aircraft. These provide redundant implementations that communicate with each other over a cross-channel bus. This component defines this side of the FGS's view of the other side.

Flight Modes (page 32) The flight modes determine which modes of operation of the FGS are active and armed at any given moment. These in term determine which fight control laws are generating the commands directing the aircraft along the lateral (roll) and vertical (pitch) axes. This component encapsulates the definitions of the lateral and vertical modes and defines how they are synchronized.

Lateral Modes (page 35) The lateral modes select the control laws generating commands directing the aircraft along the lateral, or roll, axis. This component describes the specific lateral modes present in this aircraft and defines how they are synchronized.

Roll Hold (ROLL) Mode (page 37) In Roll Hold mode the FGS generates guidance commands to hold the aircraft at a fixed bank angle. Roll Hold mode is the basic lateral mode and is always active when the modes are displayed and no other lateral mode is active.

Heading Select (HDG) Mode (page 40) In Heading Select mode, theFGS provides guidance commands to to track the Selected Heading displayed on the PFD.

Lateral Navigation (NAV) Mode (page 40) In Lateral Navigation mode, the FGS provides guidance commands to acquire and track lateral guidance for en route navigation and non-precision approaches. Lateral Navigation is an arming mode, i.e., after being selected, it must remained armed for a period of time before it can become active.

Lateral Approach (LAPPR) Mode (page 50) In Lateral Approach mode, the FGS provides guidance commands to acquire and track lateral guidance for precision and nonprecision approaches. Lateral Approach is an arming mode, i.e., after being selected, it must remained armed for a period of time before it can become active.

Go Around (GA) Mode) (page 56) In Go Around mode the FGS generates guidance commands for the pilot after aborting an approach. The AP is never engaged during Go Around mode. Lateral Go Around mode provides guidance to maintain the reference heading.

Vertical Modes (page 60) The vertical modes select the control laws generating commands directing the aircraft along the vertical, or pitch, axis. This component describes the specific vertical modes present in this aircraft and defines how they are synchronized

Pitch Hold (PITCH) Mode (page 62) In Pitch Hold mode the FGS generates guidance commands to hold the aircraft at a fixed pitch angle. Pitch Hold mode is the basic vertical mode and is always active when the modes are displayed and no other vertical mode is active.

Vertical Speed (VS) Mode (page 65) In Vertical Speed mode, the FGS provides pitch guidance commands to to hold the aircraft to the Vertical Speed (VS) reference.

Flight Level Change (FLC) Mode (page 69) In Flight Level Change mode, the FGSprovides guidance commands to acquire and track an Indicated Airspeed (IAS) or Mach Reference Airspeed, taking into account the need to climb or descend to bring the aircraft to the PreSelector Altitude (PSA).

Altitude Hold (ALT) Mode (page 73) In Altitude Hold mode, the FGS provides pitch guidance commands to to acquire and track the Altitude reference, which is set to the current altitude when the mode is activated or upon a synchronization request by the flight crew.

Altitude Select (ALTSEL) Mode (page 77) In Altitude Select mode, the FGS provides guidance commands to capture and track the Preselected Altitude. Altitude Select is an arming mode, i.e., after being selected, it must remained armed for a period of time before it can become active. Altitude Select mode is normally armed, although it is automically deselected by the activatation of

Vertical Approach, Go Around, or Altitude Hold mode. While in the armed state, the FGS monitors the aircraft closure rate towards the target altitude and determines the optimum capture point to transition to the capture state. In the capture state, the FGS generates vertical guidance commands to perform a smooth capture of the target altitude. Once it acquires the target altitude, it enters the track state, during which it generates vertical guidance commands to maintain the aircraft at the target altitude.

Vertical Approach (VAPPR) Mode (page 85)

In Vertical Approach mode, the FGS provides guidance commands to track vertical guidance for ILS precision Glideslope approaches. Vertical Approach is an arming mode, i.e., after being selected, it must remained armed for a period of time before it can become active.

Vertical Go Around (VGA) Mode (page 91)

In Go Around mode, the FGS provides guidance to the pilot after aborting an approach. The AP is never engaged during Go Around mode. Vertical Go Around mode provides guidance to maintain a fixed pitch angle.

## 2.2 Prioritization of Events

An issue that frequently arises in the specification of embedded systems is how to handle multiple events that occur at the same point in time. Here, we assume that an event corresponds to an instantaneous change in some input or state variable. One school argues that since an event occurs at a point in time, it is impossible for two events to occur at precisely the same moment, and simultaneous events should be prohibited in the underlying formal model. While theoretically appealing, many embedded systems are polling systems that periodically sample their inputs. It is difficult to imagine how a polling system could be built that could guarantee that no more than one input changes between any two samples. Even interrupt driven systems are ultimately implemented as digital systems where interrupts are only handled at well defined boundaries, such as the end of an instruction, and multiple interrupts can be observed at these boundaries.

From a practical standpoint, it seems that the required abstraction is to allow one or more events to occur at the same time, and to deal with this within the specification. $\mathrm { R S M L } ^ { - e }$ makes the one message assumption that at most one message can arrive at any given point in time. However, within a message, several fields can change value, allowing more than one input event to occur at the same time. Since we did not know how the inputs to the mode logic would be implemented in a specific system, we decided to group the inputs into large messages in order to make as few assumptions as possible about the disjointness of input events.

In verifying the behavior of the mode logic, it became clear that the behavior of the system when two or more events occurred at the same time would indeed have to be carefully considered if the system was to have the correct behavior and satisfy even the most basic of safety properties (e.g., no more than one lateral mode or vertical mode active at the same time). Our approach was to define a prioritization of the input events such that only the highest priority event is seen by the main body of the specification and the lower priority events are discarded. For example, it seems reasonable to respond to the pilot pressing the Go Around switch and ignore the copilot pressing the Flight Director switch, rather than the other way around.

This approach is reasonable for most combinations of events. However, a few events, such as the acquisition of a navigation beacon, do not need to be acted upon immediately, but should not be simply discarded. These were given the lowest possible priority, and the condition of their being true, rather than the event of their becoming true, was used to trigger the associated transitions. In this way, processing of the event might be delayed, but would always be completed as soon as no higher priority event blocked it.

Other approaches are of course feasible. For example, one could queue the input events and process them in the order received. This introduces considerable complexity into the model, and the simpler prioritization described here actually appears to be the more appropriate solution. One advantage of this approach is that it makes the solution explicit and easily reviewed.

We also attempted to localize this logic in the specification by introducing macros (predicates) of the form When\_Event\_Name\_Seen. These macros are true only when the underlying event occurs and no higher priority event has occurred at the same time. By using only the When\_Event\_Name\_Seen macros in the body of the specification, it is straightforward to change the prioritization of events, or even to implement a more complicated approach such as the queueing model discussed earlier.

As formal verification of the model proceeded, it became clear that it was possible to process some combinations of events in parallel. As a result we changed the prioritization from a total to a partial order, as shown in Figure 2.2. In this diagram, an event has a higher priority than all events that can be reached from it by following a downward chain of arrow and will supersede those events. If no path exists between two events, then the two events can be processed concurrently. Thus, pressing the SYNC switch supersedes all events except pressing the AP Disconnect or AP Engage switch, which can be processed in parallel with it. In like manner, pressing the HDG switch will supersede pressing the NAV switch, the Pilot Flying Switch, the Flight Director switch, and any of the capture or track conditions. However, a press of the HDG switch can be processed in parallel with any of the switches associated only with vertical modes, such as the ALT switch.

It is worth noting that this partial order could only have been verified with confidence through the use of formal analysis tools such as model checkers and theorem provers. A full description of this verification activity will be provided in a later report.

![](images/224fc7d34f3a779de3de0cba694eefc88d2608c837a3c9a45e748ec55a697596.jpg)  
Figure 2.2: The Partial Order of Event Priorities

## 2.3 Basic Definitions

This section defines types and constants that are used throughout the specification.

<table><tr><td></td><td>TYPE</td><td></td></tr><tr><td></td><td>Side</td><td></td></tr><tr><td>Possible Values: LEFT, RIGHT</td><td></td><td></td></tr><tr><td rowspan="2"></td><td>TYPE</td><td></td></tr><tr><td>On_Off</td><td></td></tr><tr><td>Possible Values: Off, On</td><td></td><td></td></tr><tr><td></td><td>TYPE</td><td></td></tr><tr><td>Possible Values: Cleared, Selected</td><td>Base_State</td><td></td></tr><tr><td></td><td></td><td></td></tr><tr><td></td><td>TYPE</td><td></td></tr><tr><td></td><td>Selected_State</td><td></td></tr><tr><td>Possible Values: Armed, Active</td><td></td><td></td></tr><tr><td></td><td>TYPE</td><td></td></tr><tr><td></td><td>Active_State</td><td></td></tr></table>

Possible Values: Capture, Track

## THIS\_SIDE

Units: N/A

Value: LEFT

Purpose: This constant defines which side of the FGS (channel) is being specified. The specifications of both sides, left and right, are identical except for this constant.

## 2.4 Flight Director (FD)

The Flight Director (FD) displays the pitch and roll guidance commands to the pilot and copilot on the Primary Flight Display. This component defines when the Flight Director guidance cues are turned on and off.

<table><tr><td colspan="2">Definitions of Values to be Imported</td></tr><tr><td colspan="2"></td></tr><tr><td colspan="2">MACRO</td></tr><tr><td colspan="2"></td></tr><tr><td colspan="2">When_Turn_FD_On</td></tr></table>

<table><tr><td rowspan=1 colspan=1>When_FD_Switch_Pressed. $\mathrm { S e e n } _ { \mathrm { m } - 1 0 3 } ( )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>.</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { W h e n } ( \mathrm { A P } _ { \mathrm { v - 1 3 2 } } = \mathrm { E n g a g e d } )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { O v e r s p e e d \_ C o n d i t i o n _ { m - 1 2 8 } ( ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { W h e n . L a t e r a l . M o d e \_ M a n u a l l y . S e l e c t e d _ { m - 2 6 } ( ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { W h e n . V e r t i c a l . M o d e . M a n u a l l y . S e l e c t e d { \Sigma } _ { \mathrm { m - 2 7 } } ( \Omega ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { W h e n . P i l o t . F l y i n g . T r a n s f e r _ { m - 2 9 } ( ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>。</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>Pilot $\mathrm { \Gamma _ { F l y i n g _ { v - 2 9 } } = T H I S \mathrm { \underline { { { S } } } I D E _ { L E F T } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(Mode_Annunciations. $\mathrm { { . O n } _ { v - 3 3 } ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when the onside FD is to be turned on (i.e., displayed on the PFD).

## When\_Turn\_FD\_Off

## Condition:

<table><tr><td>A N</td><td>When_FD_Switch_Pressed_Seenm-103()</td><td>T</td></tr><tr><td>D</td><td>Overspeed_Conditionm-128()</td><td>F</td></tr></table>

Purpose: This event defines when the onside FD is to be turned off (i.e., removed from the PFD).

MACRO

When\_Lateral\_Mode\_Manually\_Selected

## Condition:

<table><tr><td rowspan=1 colspan=1>PREVIOUS STEP(Mode_Annunciations. $\mathrm { { . O n _ { v - 3 3 } } ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Is_This_Side. $\mathrm { A c t i v e } _ { \mathrm { v } - 3 0 }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>When_HDG_Switch_Pressed $\mathrm { . S e e n } _ { \mathrm { m } \mathrm { - } \mathrm { 1 0 9 } } ( )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_NAV_Switch_Pressed. $\mathrm { S e e n } _ { \mathrm { m } - 1 0 8 } ( )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_APPR_Switch_Pressed. $S e e n _ { \mathrm { m - 1 1 5 } } ( \AA )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_GA_Switch_Pressed. $\mathrm { S e e n } _ { \mathrm { m } - 1 1 6 } ( )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when a lateral mode is manually selected

## When\_Vertical\_Mode\_Manually\_Selected

## Condition:

<table><tr><td rowspan=1 colspan=1>PREVIOUS STEP(Mode_Annunciations $\mathrm { { . O n _ { v - 3 3 } } ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Is_This_Side. $\mathrm { A c t i v e } _ { \mathrm { v } - 3 0 }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>When_VS_Switch_Pressed. $. \mathrm { { s e n } _ { m - 1 1 1 } ( ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_FLC_Switch_Pressed. $. \mathrm { S e e n } _ { \mathrm { m } - 1 1 2 } ( )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_ALT_Switch_Pressed. $\mathrm { S e e n } _ { \mathrm { m } - 1 1 3 } ( )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_APPR_Switch_Pressed. $S e e n _ { \mathrm { m - 1 1 5 } } ( \AA )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_GA_Switch_Pressed. $. \mathrm { S e e n } _ { \mathrm { m } - 1 1 6 } ( )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_VS_Pitch_Wheel_Rotated. $\mathrm { S e e n } _ { \mathrm { m } - 1 1 0 } ( )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>.</td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(Is_VS_Activev-66)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>.</td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(Is_VAPPR $\mathrm { A c t i v e } _ { \mathrm { v } - 8 7 } )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>.</td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(Overspeediv-128)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>*</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>+</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>.</td></tr><tr><td rowspan=1 colspan=1>When_ALTSEL_Target_Altitude_Changed. $\mathrm { S e e n } _ { \mathrm { m } - 1 1 4 } ( )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(Is_ALTSEL. $\mathrm { A c t i v e } _ { \mathrm { v } - 8 0 } )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

OR  
Purpose: This event defines when a vertical mode is manually selected.

![](images/25f6bca4b630d364085f680e48c809ac5f7969b5fa66191ae281ae93b556026f.jpg)  
Purpose: Indicates if the FD Guidance cues should be displayed on the PFD.

STATE VARIABLE

Purpose: This variable maintains the current state of the onside Flight Director.

![](images/bcd146ad54f9fe731b323eee41be1783f4896987581634c20c4f4440db4a0701.jpg)

## 2.5 Pilot Flying (PF)

The transfer switch on the FCP is used to determine which FGS provides mode annunciations and guidance commands to the PFDs while in dependent mode. This component defines which side is the Pilot Flying side. It also defines the notion of the “active" side of the FGS. A side of the FGS is said to be “active" if it is providing mode annunciations and guidance commands to its PFD.

Condition: Changed(Pilot\_Flyingv-29)

Purpose: This event occurs when the pilot flying side changes to the other side.

## 2.6 Independent Mode

Normally, the FGS operates in dependent mode in which the pilot flying (PF) side of the FGS provides the mode annunciations and FD guidance commands to both PFDs. While in dependent mode, the pilot not flying (PNF) side of the FGS synchronizes its modes to the pilot flying side. Under final approach conditions and during takeoff or go around modes, the FGS operates in independent mode in which each side operates independently of the other side and provides mode annunciations and FD guidance commands to its own PFD. This component defines when the FGS enters independent mode.

STATE VARIABLE

Purpose: A side of the FGS is said to be active if it is the source for guidance to the AP its FD. This occurs if the system is in independent mode, if this side of the FGS is the pilot flying side, or if the other side of the FGS is the pilot flying side but its mode annunciations are not turned on.

```autohotkey
Parent: NONE
Type: {Off, On}ty-23
Initial Value: Off
Classified as:State
:= On if Independent_Mode_Conditionm-31()
:= Off if not Independent_Mode_Conditionm-31()
```  
Purpose: This condition defines when the system is in independent mode. This occurs when lateral and vertical approach modes are active on both sides (channels) or vertical Go Around mode is active.

Definitions of Values to be Encapsulated

MACRO

Independent\_Mode\_Condition

## Condition:

<table><tr><td rowspan=1 colspan=1>Is_LAPPR_Activev-52</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Is_VAPPR_Activev-87</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1>Is_Offside_LAPPR_Activev-134</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1>Is_Offside_VAPPR_Activev-134</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>T  •</td></tr><tr><td rowspan=1 colspan=1>Is_VGA_Activev-92</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>Is_Offside_VGA_Activev-135</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>T</td></tr></table>

STATE VARIABLE

## Independent\_Mode

Purpose: This variable maintains the state of whether this side is in independent mode.

Comment: This variable is introduced to make it easier to access its previous value and so that it can be displayed during simulation.

![](images/1d76cf251b2ecd87b23bb2599fdc1b4a2c3afec7fd4bf2ce0c3ab65504f4d0e5.jpg)

<table><tr><td rowspan=1 colspan=1> $\mathrm { O n s i d e \mathrm { { \_ F D } _ { v - 2 8 } = O n } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>T.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { O f f s i d e \mathrm { { _ { - F D } } _ { v \mathrm { - 1 3 3 } } \mathrm { = } \mathrm { { O n } } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>· T</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s \mathrm { _ { - } A P \mathrm { \_ E n g a g e d _ { v - 1 3 1 } } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>。</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>T</td></tr></table>

## 2.7 Flight Modes

The flight modes determine which modes of operation of the FGS are active and armed at any given moment. These in term determine which fight control laws are generating the commands directing the aircraft along the lateral (roll) and vertical (pitch) axes. This component describes the lateral and vertical modes and defines how they are synchronized.

Definitions of Values to be Imported

MACRO

When\_Turn\_Modes\_On

## Condition:

Purpose: This event defines when the flight modes are to be turned on and displayed on the PFD.

MACRO

When\_Turn\_Modes\_Off

## Condition:

$$
\mathrm { | O n s i d e \mathrm { { \_ F D } _ { v - 2 8 } = O f f } }
$$

$$
\overline { { \mathrm { O f f s i d e \mathrm { . F D } _ { v \mathrm { - } 1 3 3 } = } \mathrm { O f f } } }
$$

$$
\mathrm { \Delta \mathrm { | A P _ { v - 1 3 2 } = D i s e n g a g e d } }
$$

Purpose: This event defines when the flight modes are to be turned off and removed from the PFD.

Mode\_Annunciations\_On

Parent: NoNE

Type: BOOLEAN

Initial Value: FALSE

Classified as: CONTROLLED

Purpose: Indicates if the mode annunications should be displayed on the PFD.

![](images/995b3b2f70a8488df9bfbbdfbcf733ccf04ace82b301355020125d83ea72a24e.jpg)  
Purpose: This variable maintains the current state of whether the mode annunciations are turned on or off.

## 2.7.1 Lateral Modes

The lateral modes select the control laws generating commands directing the aircraft along the lateral, or roll, axis. This component describes the specific lateral modes present in this aircraft and defines how they are synchronized.

<table><tr><td colspan="2">Definitions of Values to be Encapsulated</td></tr><tr><td colspan="2"></td></tr><tr><td rowspan="2">MACRO</td><td></td></tr><tr><td></td></tr><tr><td colspan="2">When_Nonbasic_Lateral_Mode_Activated</td></tr></table>

## Condition:

<table><tr><td rowspan=1 colspan=1>When_HDG_Activatedm-42()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>T •</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1>When_NAV_Activatedm-47()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>• T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_LAPPR_Activatedm-53()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1>When_LGA_Activatedm-58()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event ocurrs when a new lateral mode other than the basic mode becomes active. It is used to deselect active or armed modes.

Comment: Basic mode is excluded to avoid a cyclic dependency in the definition of this macro.

## Condition:

<table><tr><td rowspan=4 colspan=1>AND</td><td rowspan=1 colspan=1> $\mathrm { I s \mathrm { \_ H D G \mathrm { \_ A c t i v e } _ { v - 4 1 } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { \overline { { I s \_ N A V \_ A c t i v e _ { v - 4 6 } } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { \ l s \mathrm { \_ L A P P R \mathrm { \_ A c t i v e _ { v - 5 2 } } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { \small { \left| \mathrm { I s \_ L G A \_ A c t i v e } _ { v - 5 7 } \right. } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr></table>

Purpose: This condition indicates if no lateral mode except basic mode is active. It is used to trigger the activation of the basic lateral mode.

Comment: Basic mode is excluded to avoid a cyclic dependency in the definition of this macro.

![](images/9d2fd60edb990e0bb2cf76907d1937f87e3b530f0b95f0991fdb4e15b183222e.jpg)

## 2.7.1.1 Roll Hold (ROLL) Mode

In Roll Hold mode the FGS generates guidance commands to hold the aircraft at a fixed bank angle. Roll Hold mode is the basic lateral mode and is always active when the modes are displayed and no other lateral mode is active.

Definitions of Values to be Imported

MACRO

Select\_ROLL

## Condition:

Is\_No\_Nonbasic\_Lateral\_Mode\_Activem-36()

Modesv-34 =On

Purpose: This event defines when Roll Hold mode is to be selected. Roll Hold mode is the basic, or default, mode and is selected whenever the mode annunciations are on and no other lateral mode is active.

Comment: To avoid cyclic dependencies, the only way to select Roll Hold mode is to deselect the active lateral mode, which will automatically activate Roll Hold.

MACRO

Deselect\_ROLL

## Condition:

![](images/deb172a102f225fedb4f8a56a6de4c5eca3924e54fad240028e96c9b97c1a885.jpg)

When\_Nonbasic\_Lateral\_Mode\_Activatedm-35()

When(Modesv-34 =Off)

![](images/44cab66b3297f0de071ac2fd1fccba02052fe44ad2e4015f152f20a15812824a.jpg)

Purpose: The event defines when Roll Hold mode is to be deselected. This occurs when a new lateral mode is activated or the modes are turned off.

Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (ROLLv-39 =Selected) if TRUE

STATE VARIABLE

Purpose: Indicates if ROLL mode is selected.

STATE VARIABLE

Is\_ROLL\_Active

Purpose: Indicates if ROLL mode is selected.

Comment: Even though ROLL Selected and ROLL Active are the same value, this is defined to provide a common set of controlled variables across all modes.

<table><tr><td colspan="3">Definitions of Values to be Encapsulated</td></tr><tr><td colspan="2"></td><td></td></tr><tr><td rowspan="2"></td><td>STATE VARIABLE</td><td></td></tr><tr><td>ROLL</td><td></td></tr></table>

![](images/b63a7dacaac2d5bbaed150bfe8aa6224e7e344249ba00cc6250d8a52d080a140.jpg)

Purpose: This variable maintains the current base state of Roll Hold mode, i.e., whether it is cleared or selected. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

## 2.7.1.2 Heading Select (HDG) Mode

In Heading Select mode, the FGS provides guidance commands to to track the Selected Heading displayed on the PFD.

Definitions of Values to be Imported

MACRO

Select\_HDG

Condition: When\_HDG\_Switch\_Pressed\_Seenm-109()

Purpose: This event defines when Heading Select mode is to be selected.

MACRO

Deselect\_HDG

## Condition:

<table><tr><td rowspan=1 colspan=1>When_HDG_Switch_Pressed_Seenm-109()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T·</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Nonbasic_Lateral_Mode_Activatedm-35()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1><img src="images/9898d9eeb8f3c31c90786d20608d8a6a877958640ad023e7cbcc13e99c66ac4e.jpg"/></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Pilot_Flying-Transferm-29()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When(Modesv-34 =Off)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when Heading Select mode is to be deselected.

<table><tr><td colspan="2">Definitions of Values to be Exported</td></tr><tr><td></td><td></td></tr><tr><td>STATE VARIABLE</td><td></td></tr><tr><td>Is_HDG_Selected</td><td></td></tr></table>

Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (HDGv-43 =Selected) if TRUE

Purpose: Indicates if HDG mode is selected.

STATE VARIABLE

Is\_HDG\_Active  
Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (HDGv-43 =Selected) if TRUE

Purpose: Indicates if HDG mode is active.

Comment: Even though HDG Selected and HDG Active are the same value, this is defined to provide a common set of controlled variables across all modes.

## When\_HDG\_Activated

## Condition:

<table><tr><td rowspan="3">A N D</td><td> $\mathrm { S e l e c t \mathbf { \mathrm { . H D G } _ { m - 4 0 } } ( ) }$ </td></tr><tr><td> $\mathrm { P R E V I O U S ~ S T E P ( H D G _ { v - 4 3 } ) }$  =Selected</td></tr><tr><td> $\mathrm { I s \mathrm { . } T h i s \mathrm { . } S i d e \mathrm { . } A c t i v e _ { v - 3 0 } }$ </td></tr></table>

![](images/af1900bce73a64187e4b80846d69eebff6d1302a9cc77f9766a2f2df97113e65.jpg)

Purpose: This signal occurs when Heading Select mode is activated.

Comment: This event is defined this way to avoid circular dependencies. It would be preferable to define it as When(HDG = Selected).

<table><tr><td colspan="3">Definitions of Values to be Encapsulated</td></tr><tr><td colspan="2"></td><td></td></tr><tr><td rowspan="2"></td><td>STATE VARIABLE</td><td></td></tr><tr><td></td><td></td></tr><tr><td colspan="3">HDG</td></tr></table>

Parent: Modesy-34.On

Type: {Cleared, Selected }ty-23

Initial Value: UNDEFINED

Classified as: State

Purpose: This variable maintains the current base state of HeadingSelect mode, i.e., whether it is cleared or selected. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

:= Offside\_HDGv-136 if not Is\_This\_Side\_Activev-30

![](images/9f78c864a8c491a3532e58bb49ff2c75fd1f41f0df6e90c6aee56ec564cadc51.jpg)

<table><tr><td>MACRO</td><td></td></tr><tr><td colspan="2"></td></tr><tr><td colspan="2">Activate_NAV</td></tr></table>

<table><tr><td>Definitions of Values to be Imported</td></tr><tr><td></td></tr><tr><td>MACRO</td></tr><tr><td>Select_NAV</td></tr></table>

## 2.7.1.3 Navigation (NAV) Mode

In Lateral Navigation mode, the FGS provides guidance commands to acquire and track lateral guidance for en route navigation and non-precision approaches. Lateral Navigation is an arming mode, i.e., after being selected, it must remained armed for a period of time before it can become active.

Condition: When\_NAV\_Switch\_Pressed $\mathrm { S e e n } _ { \mathrm { m } - 1 0 8 } ( )$

Purpose: This event defines when Lateral Navigation mode is to be selected, i.e., to become armed.

Condition: When\_NAV\_Track\_Cond\_Met $\mathrm { S e e n } _ { \mathrm { m } \mathrm { - } 9 5 } ( )$

Purpose: This event defines when Lateral Navigation mode is to transition from the armed to the active state.

## Deselect\_NAV

## Condition:

AND

OR

<table><tr><td rowspan=3 colspan=8>A</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td></tr><tr><td rowspan=3 colspan=1>ND</td><td rowspan=1 colspan=1>When_Selected_Nav_Frequency_Changedv-127</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1><img src="images/d6382ce8610965daece591f531a93d5e36a1138b2dcd0d9126651d317ccf4d40.jpg"/></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Pilot_Flying-Transferm-29()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>.</td></tr><tr><td rowspan=1 colspan=1>When(Modesv-34 =Off)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when Lateral Navigation mode is to be deselected, i.e., to be cleared regardless of whether it is armed or active.

MACRO

## Dearm\_NAV

Condition: When\_LAPPR\_Armedm-53()

Purpose: This event defines when Lateral Navigation mode is to be cleared if it is armed, but to remain active if it is active.

MACRO

## Deactivate\_NAV

Condition: When\_Nonbasic\_Lateral\_Mode\_Activatedm-35()

Purpose: This event defines when Lateral Navigation mode is to be cleared if it is active, but to remain armed if it is armed.

Definitions of Values to be Exported

STATE VARIABLE

Is\_NAV\_Selected

Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (NAVv-48 =Selected) if  TRUE

Purpose: Indicates if NAV mode is selected.

STATE VARIABLE

Is\_NAV\_Active  
Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (NAV\_Selectedv-49 =Active) if TRUE

Purpose: Indicates if NAV mode is active.

# When\_NAV\_Armed

## Condition:

<table><tr><td rowspan=3 colspan=1>AND</td><td rowspan=1 colspan=1>Select_NAVm-44()</td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(NAVv-48) =Cleared</td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>Is_This_Side_Activev-30</td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This signal occurs when Lateral NAV mode is armed.

Comment: This event is defined this way to avoid circular dependencies. It would be preferable to define it as When(NAV\_Selected = Armed).

MACRO

## When\_NAV\_Activated

## Condition:

<table><tr><td rowspan=3 colspan=1>AND</td><td rowspan=1 colspan=1>Activate_NAVm-44()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(NAV_Selectedv-49) =Armed</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>Is_This_Side_Activev-30</td><td rowspan=1 colspan=2>T</td></tr></table>

Purpose: This signal occurs when Lateral Navigation mode is activated.

Comment: This event is defined this way to avoid circular dependencies. It would be preferable to define it as When(NAV\_Selected = Active).

![](images/dd7526c5c3a2e959cb0b903a13a399ea827a4d8ab567ec4cd45849d2c7196c3f.jpg)  
Purpose: This variable maintains the current base state of Lateral Navigation mode, i.e., whether it is cleared or selected. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

![](images/b217ac683e7a7bff9585cdd78dcbd518d01008c1f437faf7cfcc8022b40653e5.jpg)  
Purpose: This variable maintains the current state of Lateral Navigation mode when it is selected, i.e., whether it is armed or active. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

## 2.7.1.4 Lateral Approach (LAPPR) Mode

In Lateral Approach mode, the FGS provides guidance commands to acquire and track lateral guidance for precision and non-precision approaches. Lateral Approach is an arming mode, i.e. after being selected, it must remained armed for a period of time before it can become active.

Definitions of Values to be Imported

MACRO

## Select\_LAPPR

Condition: When\_APPR\_Switch\_Pressed\_Seenm-115()

Purpose: This event defines when Lateral Approach mode is to be selected, i.e., to become armed.

MACRO

## Activate\_LAPPR

## Condition: When\_LAPPR\_Track\_Cond\_Met\_Seenm-98()

Purpose: This event defines when Lateral Approach mode is to transition from the armed to the active state.

## Deselect\_LAPPR

## Condition:

OR

<table><tr><td rowspan=1 colspan=1>When_APPR_Switch_Pressed_Seenm-115()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Selected_Nav_Source_Changedy-127</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Selected_Nav_Frequency_Changedy-127</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1><img src="images/498b505f708ee238de0c84cb4148524a69cdac333b6c1a151b480366c0d08523.jpg"/></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Pilot_Flying-Transferm-29()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When(Modesv-34 =Off)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when Lateral Approach mode is to be deselected, i.e., to be cleared regardless of whether it is armed or active.

MACRO

## Dearm\_LAPPR

## Condition: When\_NAV\_Armedm-47()

Purpose: This event defines when Lateral Approach mode is to be cleared if it is armed, but to remain active if it is active.

MACRO

## Deactivate\_LAPPR

Condition: When\_Nonbasic\_Lateral\_Mode\_Activatedm-35()

Purpose: This event defines when Lateral Approach mode is to be cleared if it is active, but to remain armed if it is armed.

Definitions of Values to be Exported

STATE VARIABLE

Is\_LAPPR\_Selected  
Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (LAPPRv-54 =Selected)if TRUE

Purpose: Indicates if LAPPR mode is selected.

STATE VARIABLE

Is\_LAPPR\_Active  
Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (LAPPR\_Selectedv-55 =Active) if TRUE

Purpose: Indicates if LAPPR mode is active.

# When\_LAPPR\_Armed

## Condition:

<table><tr><td rowspan=3 colspan=1>AND</td><td rowspan=1 colspan=1>Select_LAPPRm-50()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(LAPPRv-54) =Cleared</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>Is_This_Side_Activev-30</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This signal occurs when Lateral Approach mode is armed.

Comment: This event is defined this way to avoid circular dependencies. It would be preferable to define it as When(LAPPR\_Selected = Armed).

MACRO

## When\_LAPPR\_Activated

## Condition:

![](images/72b6fb42df35dad1b75e54e6ee90ad7a5e14728ab4c081d888cab348c01bdc72.jpg)

Purpose: This signal occurs when Lateral Approach mode is activated.

Comment: This event is defined this way to avoid circular dependencies. It would be preferable to define it as When(LAPPR\_Selected = Active).

<table><tr><td rowspan=1 colspan=7>Definitions of Values to be Encapsulated</td></tr><tr><td rowspan=1 colspan=7>STATE VARIABLELAPPR</td></tr><tr><td></td><td></td><td></td><td></td><td rowspan=1 colspan=2>T</td><td></td></tr><tr><td></td><td></td><td></td><td></td><td rowspan=1 colspan=2>T</td><td></td></tr><tr><td></td><td></td><td></td><td></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td></td></tr><tr><td></td><td></td><td></td><td></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td></td></tr><tr><td></td><td rowspan=1 colspan=1> $\mathrm { L A P P R } _ { \mathrm { m - 5 1 } } ( \AA )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td></td><td rowspan=1 colspan=1> $\mathrm { { L A P P R } _ { m - 5 1 } ( ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td></td><td rowspan=1 colspan=1> $\mathrm { L A P P R } _ { \mathrm { m - 5 1 } } ( \AA )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td></td><td rowspan=1 colspan=1> $\mathrm { A c t i v e } _ { \mathrm { v } - 3 0 }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>T</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This variable maintains the current base state of Lateral Approach mode, i.e., whether it is cleared or selected. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

![](images/e29eea8b87931a22d9ebb5a1693171d6ffcaae54d82b738f552c2c80a0bb62f5.jpg)

Purpose: This variable maintains the current state of Lateral Approach mode when it is selected, i.e., whether it is armed or active. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

## 2.7.1.5 Lateral Go Around (LGA) Mode

In Go Around mode the FGS generates guidance commands for the pilot after aborting an approach. The AP is never engaged during Go Around mode. Lateral Go Around mode provides guidance to maintain the reference heading.

<table><tr><td>Definitions of Values to be Imported</td></tr><tr><td></td></tr><tr><td>MACRO</td></tr><tr><td>Select_LGA</td></tr></table>

## Condition:

<table><tr><td rowspan=1 colspan=1>When_GA_Switch_Pressed_Seenm-116()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>Overspeed_Conditionm-128()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr></table>

Purpose: This event defines when Lateral Go Around mode is to be selected.

MACRO

Deselect\_LGA

## Condition:

<table><tr><td rowspan=1 colspan=1> $\mathrm { W h e n } ( \mathrm { A P } _ { \mathrm { v - 1 3 2 } } = \mathrm { E n g a g e d } )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { W h e n . N o n b a s i c . L a t e r a l . M o d e . A c t i v a t e d _ { m - 3 5 } ( ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Nonbasic_Vertical_Mode_Activatedm-60()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1><img src="images/3200495d24d5c1a18d43d57eb9c9fe59d701aefc73c36a083a5f9a2e630ae9ec.jpg"/></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $D \left| \mathrm { W h e n . S Y N C . S w i t c h . P r e s s e d . S e e n } _ { \mathrm { m . 1 1 7 } } ( ) \right.$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { W h e n . P i l o t \mathrm { { \_ F l y i n g \mathrm { . } T r a n s f e r _ { m - 2 9 } ( \Omega ) } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>.</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { W h e n ( M o d e s _ { v - 3 4 } = O f f ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when Lateral Go Around mode is to be deselected.

<table><tr><td colspan="2">Definitions of Values to be Exported</td></tr><tr><td></td><td></td></tr><tr><td>STATE VARIABLE</td><td></td></tr><tr><td>Is_LGA_Selected</td><td></td></tr></table>

Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (LGAv-59 =Selected) if TRUE

Purpose: Indicates if LGA mode is selected.

STATE VARIABLE

Is\_LGA\_Active  
```makefile
Parent: NONE
Type: BOOLEAN
Initial Value: FALSE
Classified as: CONTROLLED
:=  (LGAv-59 =Selected) if TRUE
```

Purpose: Indicates if LGA mode is active.

Comment: Even though LGA Selected and LGA Active are the same value, this is defined to provide a common set of controlled variables across all modes.

## When\_LGA\_Activated

## Condition:

<table><tr><td rowspan=4 colspan=1>AND</td><td></td><td></td><td></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { S e l e c t \bot G A _ { m - 5 6 } ( ) }$ </td><td rowspan=1 colspan=2>T</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { P R E V I O U S ~ S T E P ( L G A _ { v - 5 9 } ) = S e l e c t e d }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s \mathrm { _ { - } T h i s \mathrm { _ { - } S i d e \mathrm { _ { - } A c t i v e _ { v - 3 0 } } } } }$ </td><td rowspan=1 colspan=2>T</td></tr></table>

Purpose: This signal occurs when Lateral Go Around mode is activated.

Comment: This event is defined this way to avoid circular dependencies. It would be preferable to define it as When(LGA = Selected).

![](images/44f46e8bb40bec6320b291b587335e8ee02c7958f13f8b1ebf3a061fdac346e2.jpg)

Purpose: This variable maintains the current state of Lateral Go Around mode. Note that if this side is not active, it obtains its value from the off side. The normal transitions for Lateral Go Around mode occur only when this side is active.

## 2.7.2 Vertical Modes

The vertical modes select the control laws generating commands directing the aircraft along the vertical, or pitch, axis. This component describes the specific vertical modes present in this aircraft and defines how they are synchronized.

<table><tr><td colspan="2">Definitions of Values to be Encapsulated</td></tr><tr><td colspan="2"></td></tr><tr><td rowspan="2"></td><td></td></tr><tr><td>MACRO</td></tr><tr><td colspan="2">When_Nonbasic_Vertical_Mode_Activated</td></tr></table>

<table><tr><td rowspan=1 colspan=1> $\mathrm { W h e n \mathrm { { . } V S \mathrm { { . } A c t i v a t e d \mathrm { { . } 6 7 } } } ( ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>·</td></tr><tr><td rowspan=1 colspan=1> $\overline { { \mathrm { W h e n . F L C . A c t i v a t e d } _ { \mathrm { m . 7 1 } } ( \ v u ) } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\overline { { \mathrm { W h e n . A L T . A c t i v a t e d } _ { \mathrm { m . 7 5 } } ( \ v u ) } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { \overline { { W h e n . A L T S E L . A c t i v a t e d _ { m - 8 1 } ( \Omega ) } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { W h e n { \_ } V A P P R { \_ } A c t i v a t e d _ { m - 8 8 } } ( )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\left| \mathrm { W h e n \_ V G A \_ A c t i v a t e d } _ { \mathrm { m \cdot 9 3 } } ( \right)$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event indicates when a new vertical mode other than the basic mode becomes active. It is used to deselect active or armed modes.  
Comment: Basic mode is excluded to avoid a cyclic dependency in the definition of this macro.

## Condition:

<table><tr><td rowspan=7 colspan=1>AND</td><td></td><td></td><td></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s \mathrm { _ V S \mathrm { _ A c t i v e _ { v - 6 6 } } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s \mathrm { { \_ F L C \mathrm { _ { - } A c t i v e _ { v - 7 1 } } } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s \mathrm { - } A L T \mathrm { - } A c t i v e _ { v - 7 4 } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s \_ A L T S E L \_ A c t i v e } _ { \mathrm { v } - \mathrm { 8 0 } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s \mathrm { . } V A P P R \mathrm { . } A c t i v e _ { v - 8 7 } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s \mathrm { _ V G A \mathrm { _ - A c t i v e } _ { v - 9 2 } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr></table>

Purpose: This condition indicates if no vertical mode except basic mode is active. It is used to trigger the activation of the basic lateral mode.

Comment: Basic mode is excluded to avoid a cyclic dependency in the definition of this macro.

<table><tr><td><img src="images/fb71ca1353744775e21c90cc75023a4fbedd7605089b1d0ce24ce2512b8303c7.jpg"/> Modesv-34 =On</td><td>Is_No_Nonbasic_Vertical_Mode_Activem-61()</td><td></td></tr><tr><td>D</td><td></td><td></td></tr></table>

## 2.7.2.1 Pitch Hold (PITCH) Mode

In Pitch Hold mode the FGS generates guidance commands to hold the aircraft at a fixed pitch angle. Pitch Hold mode is the basic vertical mode and is always active when the modes are displayed and no other vertical mode is active.

Definitions of Values to be Imported

MACRO

Select\_PITCH

## Condition:

Purpose: Pitch Hold mode is the basic, or default, mode and is selected whenever the mode annunciations are on and no other vertical mode is active.

Comment: To avoid cyclic dependencies, the only way to select Pitch Hold mode is to deselect the active vertical mode, which will automatically activate Pitch Hold mode.

MACRO

Deselect\_PITCH

## Condition:

OR

<table><tr><td rowspan=1 colspan=1>When_Nonbasic_Vertical_Mode_Activatedm-60()</td><td rowspan=1 colspan=1><img src="images/e1e822eb4f2ff0db15817ac158964118ef522079be3caef24362f59c32ce835c.jpg"/></td></tr><tr><td rowspan=1 colspan=1>When(Modesv-34 =Off)</td><td rowspan=1 colspan=1>·T</td></tr></table>

Purpose: Pitch Hold mode is deselected when: a new vertical mode is activated or the modes are turned off.

Definitions of Values to be Exported

STATE VARIABLE

Is\_PITCH\_Selected  
Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (PITCHv-64 =Selected) if TRUE

Purpose: Indicates if PITCH mode is selected.

STATE VARIABLE

Is\_PITCH\_Active  
Parent: NONE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (PITCHv-64 =Selected) if TRUE

Purpose: Indicates if PITCH mode is active.

Comment: Even though PITCH Selected and PITCH Active are the same value, this is defined to provide a common set of controlled variables across all modes.

![](images/51c35d7e21e7200c70853f9bc83271000f877ef0b53e5f681cdd2a23d0ede2ca.jpg)

Purpose: This variable maintains the current base state of Pitch Hold mode, i.e., whether it is cleared or selected. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

## 2.7.2.2 Vertical Speed (VS) Mode

In Vertical Speed mode, the FGS provides pitch guidance commands to to hold the aircraft to the Vertical Speed (VS) reference.

Definitions of Values to be Imported

MACRO

Select\_VS

## Condition:

<table><tr><td rowspan=1 colspan=1>When_VS_Switch_Pressed_Seenm-111()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>Overspeed_Conditionm-128()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1><img src="images/e1aecbba0478fb40bf4665ecca373c38df27029a81192ded4f4c45b9d2b012e8.jpg"/></td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(Is_VAPPR_Activev-87)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr></table>

Purpose: This event defines when Vertical Speed mode is to be selected.

MACRO

Deselect\_VS

## Condition:

Purpose: This event defines when Vertical Speed mode is to be deselected.
<table><tr><td></td><td rowspan=1 colspan=1>When_VS_Switch_Pressed_Seenm-111()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>T·</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td></td><td rowspan=1 colspan=1>When_Nonbasic_Vertical_Mode_Activatedm-60()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2><img src="images/334113797e3c60c3a4c58658d62e66d11bf61896a3704fdec0ff124e5eca5565.jpg"/></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=2 colspan=1>D</td><td rowspan=1 colspan=1>When_Pilot_Flying-Transferm-29()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When(Modesv-34 =Off)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

STATE VARIABLE

Is\_VS\_Selected

```makefile
Parent: NONE
Type: BOOLEAN
Initial Value: FALSE
Classified as: CONTROLLED
:= (VSv-68 =Selected) if TRUE
```

Purpose: Indicates if VS mode is selected.

STATE VARIABLE

Is\_VS\_Active

Purpose: Indicates if VS mode is active.

Comment: Even though VS Selected and VS Active are the same value, this is defined to provide a common set of controlled variables across all modes.

## Condition:

<table><tr><td rowspan=1 colspan=1> $\mathrm { S e l e c t . { V S } _ { \mathrm { m - 6 5 } } ( ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(VSv-68) =Selected</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s \mathrm { _ { - } T h i s \mathrm { _ { - } S i d e \mathrm { _ { - } A c t i v e _ { v - 3 0 } } } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This signal occurs when Vertical Speed mode is activated.

Comment: This event is defined this way to avoid circular dependencies. It would be preferable to define it as When(VS = Selected).

![](images/75233dcd231b7acc756155d7decd215390a1c4a4b0dc4ff8f660a9941643bc05.jpg)

Purpose: This variable maintains the current base state of Vertical Speed mode, i.e., whether it is cleared or selected. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

## 2.7.2.3 Flight Level Change (FLC) Mode

In Flight Level Change mode, the FGS provides guidance commands to acquire and track an Indicated Airspeed (IAS) or Mach Reference Airspeed, taking into account the need to climb or descend to bring the aircraft to the PreSelector Altitude (PSA).

<table><tr><td>Definitions of Values to be Imported</td></tr><tr><td></td></tr><tr><td>MACRO</td></tr><tr><td>Select_FLC</td></tr></table>

## Condition:

<table><tr><td rowspan=1 colspan=1>When_FLC_Switch_Pressed_Seenm-112()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(Is_VAPPR_Activev-87)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1>Overspeed_Conditionm-128()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(Is_ALT_Activev-74)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1>When_ALT_Activatedm-75()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(Is_ALTSEL_Activev-80)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1>When_ALTSEL $\mathrm { A c t i v a t e d } _ { \mathrm { m } - 8 1 } ( )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>F</td></tr></table>

Purpose: This event defines when Flight Level Change mode is to be selected.

<table><tr><td rowspan=1 colspan=1> $\mathrm { | W h e n . F L C . S w i t c h . P r e s s e d . S e e n _ { m - 1 1 2 } ( ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { W h e n . V S . P i t c h . W h e e l . R o t a t e d . S e e n } _ { \mathrm { m - 1 1 0 } } ( \AA )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { \mathrm { O v e r s p e e d . C o n d i t i o n _ { m - 1 2 8 } ( ) } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1><img src="images/fac53848779c5c826b3f6b999147db2f2c7bfd740944ac81219d21a438c6fb99.jpg"/></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { W h e n . N o n b a s i c . V e r t i c a l . M o d e . A c t i v a t e d _ { m - 6 0 } ( ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { W h e n . P i l o t \mathrm { { \_ F l y i n g \mathrm { _ { - } } T r a n s f e r _ { \mathrm { { m - 2 9 } } } ( \Omega ) } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { \overline { { W h e n ( M o d e s _ { v - 3 4 } = O f f ) } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when Flight Level Change mode is to be deselected.

Definitions of Values to be Exported

STATE VARIABLE

Is\_FLC\_Selected

Parent: NoNE

Type: BOOLEAN

Initial Value: FALSE

Classified as: CONTROLLED

Purpose: Indicates if FLC mode is selected.

## Is\_FLC\_Active

Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (FLCv-72 =Selected) if TRUE

Purpose: Indicates if FLC mode is active.

Comment: Even though FLC Selected and FLC Active are the same value, this is defined to provide a common set of controlled variables across all modes.

MACRO

## When\_FLC\_Activated

## Condition:

<table><tr><td rowspan=1 colspan=1> $\overline { { \mathrm { S e l e c t \_ F L C _ { m - 6 9 } ( ) } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { P R E V I O U S ~ S T E P ( F L C _ { v - 7 2 } ) }$ =Selected</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { \underline { { I s \mathrm { . } T h i s \mathrm { . } S i d e \mathrm { . } A c t i v e _ { v - 3 0 } } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This signal occurs when Flight Level Change mode is activated.

Comment: This event is defined this way to avoid circular dependencies. It would be preferable to define it as When(FLC = Selected).

![](images/1abc2a878255db66309b8dc82d737ef662099ad9445fa7231cce435124a809b2.jpg)  
Purpose: This variable maintains the current state of Flight Level Change mode. Note that if this side is not active, it obtains its value from the off side. The normal transitions for Heading Select mode occur only when this side is active.

<table><tr><td>MACRO</td></tr><tr><td></td></tr><tr><td>Deselect_ALT</td></tr></table>

## 2.7.2.4 Altitude Hold (ALT) Mode

In Altitude Hold mode, the FGS provides pitch guidance commands to to acquire and track the Altitude reference, which is set to the current altitude when the mode is activated or upon a synchronization request by the flight crew.

<table><tr><td>Definitions of Values to be Imported</td></tr><tr><td></td></tr><tr><td>MACRO</td></tr><tr><td>Select_ALT</td></tr></table>

## Condition:

<table><tr><td rowspan=1 colspan=1>When_ALT_Switch_Pressed_Seenm-113()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(Is_VAPPR_Activev-87)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1>When_ALTSEL_Target_Altitude_Changed_Seenm-114()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>PREVIOUS STEP(Is_ALTSEL_Trackv-80)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when Altitude Hold mode is to be selected.

## Condition:

<table><tr><td rowspan=1 colspan=1>When_ALT_Switch_Pressed_Seenm-113()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_VS_Pitch_Wheel_Rotated_Seenm-110()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Nonbasic_Vertical_Mode_Activatedm-60()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1><img src="images/c8b7d4782c8f4bf0c91d570f9ab4f4490a86802a180613f4c2bb889f5177b59e.jpg"/></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Pilot_Flying-Transferm-29()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When(Modesv-34 =Off)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when Altitude Hold mode is to be deselected.

Parent: NONE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (ALTv-76 =Selected) if TRUE

STATE VARIABLE

Is\_ALT\_Selected

Purpose: Indicates if ALT mode is selected.

STATE VARIABLE

Is\_ALT\_Active

Parent: NONE

Purpose: Indicates if ALT mode is active.

Comment: Even though ALT Selected and ALT Active are the same value, this is defined to provide a common set of controlled variables across all modes.

## When\_ALT\_Activated

## Condition:

<table><tr><td rowspan=3 colspan=1>AND</td><td rowspan=1 colspan=1> $\mathrm { S e l e c t \_ A L T _ { m - 7 3 } ( ) }$ </td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { P R E V I O U S ~ S T E P } ( \mathrm { A L T _ { v - 7 6 } } ) = \mathrm { S e l e c t e d }$ </td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s \mathrm { _ { - } T h i s \mathrm { _ { - } S i d e \mathrm { _ { - } A c t i v e _ { v - 3 0 } } } } }$ </td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This signal occurs when Altitude Hold mode is activated.

Comment: This event is defined this way to avoid circular dependencies. It would be preferable to define it as When(ALT = Selected).

<table><tr><td colspan="3">Definitions of Values to be Encapsulated</td></tr><tr><td colspan="2"></td><td></td></tr><tr><td></td><td>STATE VARIABLE</td><td></td></tr><tr><td colspan="3">ALT</td></tr></table>

![](images/db7cff62b6cc1f1054b41988bbbad521a8111d77cbd858c054ca23f348e6e7f8.jpg)

Purpose: This variable maintains the current base state of Altitude Hold mode, i.e., whether it is cleared or selected. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

## 2.7.2.5 Altitude Select (ALTSEL) Mode

In Altitude Select mode, the FGS provides guidance commands to capture and track the Preselected Altitude. Altitude Select is an arming mode, i.e., after being selected, it must remained armed for a period of time before it can become active. Altitude Select mode is normally armed, although it is automically deselected by the activatation of Vertical Approach, Go Around, or Altitude Hold mode. While in the armed state, the FGS monitors the aircraft closure rate towards the target altitude and determines the optimum capture point to transition to the capture state. In the capture state, the FGS generates vertical guidance commands to perform a smooth capture of the target altitude. Once it acquires the target altitude, it enters the track state, during which it generates vertical guidance commands to maintain the aircraft at the target altitude.

<table><tr><td>Definitions of Values to be Imported</td></tr><tr><td></td></tr><tr><td>MACRO</td></tr><tr><td></td></tr><tr><td>Select_ALTSEL</td></tr></table>

## Condition:

<table><tr><td rowspan=5 colspan=1>AND</td><td></td><td></td><td></td></tr><tr><td rowspan=1 colspan=1>Is_VAPPR_Activev-87</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s _ { - } V G A \mathrm { _ { - } A c t i v e _ { v - 9 2 } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s . A L T \mathrm { \_ A c t i v e } _ { v - 7 4 } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { M o d e s } _ { \mathrm { v - 3 4 } } = \mathrm { O n }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when Altitude Select mode is to be selected, i.e., to become armed. Altitude Select mode is armed or active except when Vertical Approach, Go Around, or Altitude Hold are active.

## Capture\_ALTSEL

Condition: When\_ALTSEL\_Capture\_Cond\_Met. $S e e n _ { \mathrm { m - 9 7 } } ( )$

Purpose: This event defines when Altitude Select mode is to transition from the armed to the capture state.

MACRO

Track\_ALTSEL

Condition: When\_ALTSEL\_Track\_Cond\_Met. $S e e n _ { \mathrm { m - 9 6 } } ( )$

Purpose: This event defines when Altitude Select mode is to transition from the capture to the track state.

MACRO

Deselect\_ALTSEL

## Condition:

<table><tr><td rowspan=1 colspan=1> $\mathrm { I s \mathrm { _ V A P P R \mathrm { \_ A c t i v e _ { v - 8 7 } } } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>T·</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s . V G A \mathrm { \_ A c t i v e } _ { v - 9 2 } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1><img src="images/5a8807efd6577ebd60d21456230feb64b58605ca215c03c2e5786f60ae7a0114.jpg"/></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s \_ A L T \_ A c t i v e _ { v - 7 4 } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { W h e n ( M o d e s _ { v - 3 4 } = O f f ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when Altitude Select mode is to be deselected, i.e., to be cleared regardless of whether it is armed or active. Altitude Select mode is armed or active except when Vertical Approach, Go Around, or Altitude Hold are active.

MACRO

## Deactivate\_ALTSEL

## Condition:

OR

<table><tr><td rowspan=1 colspan=1>When_ALTSEL_Target_Altitude_Changed_Seenm-114()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>T·</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_VS_Pitch_Wheel_Rotated_Seenm-110()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1><img src="images/bf3483657bc52cded52dd4ee2ecb2e42638ba172f2b77173e1be005daf343a29.jpg"/></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Pilot_Flying-Transferm-29()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Nonbasic_Vertical_Mode_Activatedm-60()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when Altitude Select mode is to be cleared if it is active, but to remain armed if it is armed.

Definitions of Values to be Exported

STATE VARIABLE

Is\_ALTSEL\_Selected

Parent: NoNE

Type: BOOLEAN

Initial Value: FALSE

Classified as: CONTROLLED

:= (ALTSELv-82 =Selected) if TRUE

Purpose: Indicates if ALTSEL mode is selected.

Is\_ALTSEL\_Active  
Parent: NONE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (ALTSEL\_Selectedv-83 =Active) if TRUE

Purpose: Indicates if ALTSEL mode is active.

STATE VARIABLE

Is\_ALTSEL\_Track  
Parent: NONE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (ALTSEL\_Activev-84 =Track) if TRUE

Purpose: Indicates if ALTSEL mode is tracking.

## Condition:

![](images/dbefd442495ac0d7900c139928358105a43c87d24978f60d09583a98c22a43d6.jpg)

Purpose: This signal occurs when Altitude Select mode is activated, i.e., it enters the capture state.

Comment: This event is defined this way to avoid circular dependencies. It would be preferable to define it as When(ALTSEL\_Selected = Active).

<table><tr><td colspan="2">Definitions of Values to be Encapsulated</td></tr><tr><td colspan="2"></td></tr><tr><td></td><td>STATE VARIABLE</td></tr><tr><td colspan="2">ALTSEL</td></tr></table>

![](images/64ab6450745a3c6b61793ba57850703ca90578e18768440f016d9766f30afdf3.jpg)

Purpose: This variable maintains the current base state of Altitude Select mode, i.e., whether it is cleared or selected. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

![](images/3ea26c9ba51058ace5d3ef7f905e4107a7e448accdef7e729b3ab7c7f35cacbf.jpg)  
Purpose: This variable maintains the current state of Altitude Select mode when it is selected, i.e., whether it is armed or active. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

## ALTSEL\_Active

Parent: Modesv-34.On  ALTSELv-82.Selected  ALTSEL\_Selectedv-83.Active

Type: {Capture, Track}ty-23

Initial Value: UNDEFINED

Classified as: State

:= Offside\_ALTSEL\_Activev-142 if not Is\_This\_Side\_Activev-30

UNDEFINED Capture if TRUE

Capture  Track if Track\_ALTSELm-78()

Purpose: This variable maintains the current state of Altitude Select mode when it is active, i.e., whether it is captured or tracking. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

## 2.7.2.6 Vertical Approach (VAPPR) Mode

In Vertical Approach mode, the FGS provides guidance commands to track vertical guidance for ILS precision Glideslope approaches. Vertical Approach is an arming mode, i.e., after being selected, it must remained armed for a period of time before it can become active.

Definitions of Values to be Imported

MACRO

Select\_VAPPR

Condition: When\_APPR\_Switch\_Pressed\_Seenm-115()

Purpose: This event defines when Vertical Approach mode is to be selected.

MACRO

Activate\_VAPPR

## Condition:

<table><tr><td rowspan=3 colspan=1><img src="images/bb3c3126cbd42d826aaa56c82a03291e948fb7fc122d2e93880fb71ad7d761fd.jpg"/></td><td rowspan=1 colspan=1>When_VAPPR_Track_Cond_Met_Seenm-99()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>Is_LAPPR_Activev-52</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1><img src="images/7fbc355b0ba4c1af6defc87863be0e497378a5d61aa176adcd2166d070d7bb17.jpg"/></td></tr><tr><td rowspan=1 colspan=1>Overspeed_Conditionm-128()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr></table>

Purpose: This event defines when Vertical Approach mode is to transition from the armed to the active state.

## Deselect\_VAPPR

## Condition:

<table><tr><td rowspan=1 colspan=1>When_APPR_Switch_Pressed_Seenm-115()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>#</td></tr><tr><td rowspan=1 colspan=1>When(Is_LAPPR_Selectedv-52 =FALSE)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Selected_Nav_Source_Changedy-127</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1>When_Selected_Nav_Frequency_Changedv-127</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Pilot_Flying_Transferm-29()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>·</td></tr><tr><td rowspan=1 colspan=1>When(Modesv-34 =Off)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when Vertical Approach mode is to be deselected, i.e., to be cleared regardless of whether it is armed or active.

MACRO

## Deactivate\_VAPPR

## Condition:

When\_Nonbasic\_Vertical\_Mode\_Activatedm-60()

Purpose: This event defines when Vertical Approach mode is to be cleared if it is active, but to remain armed if it is armed.

Definitions of Values to be Exported

STATE VARIABLE

Is\_VAPPR\_Selected

Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (VAPPRv-89 =Selected) if TRUE

Purpose: Indicates if VAPPR mode is selected.

STATE VARIABLE

Is\_VAPPR\_Active  
Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (VAPPR\_Selectedv-90 =Active) if TRUE

Purpose: Indicates if VAPPR mode is active.

# When\_VAPPR\_Activated

## Condition:

<table><tr><td rowspan=3 colspan=1>AND</td><td rowspan=1 colspan=1> $\mathrm { A c t i v a t e \_ V A P P R _ { m - 8 5 } ( ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { P R E V I O U S ~ S T E P } ( \mathrm { V A P P R . S e l e c t e d } _ { \mathrm { v - 9 0 } } ) = \mathrm { A r m e d }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1><img src="images/3922a33429050743edff9097670861ab5a560472fc2ddb98b6c7940766390306.jpg"/></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s \mathrm { . } T h i s \mathrm { . } S i d e \mathrm { . } A c t i v e _ { v - 3 0 } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This signal occurs when Vertical Approach mode is activated.

Comment: This event is defined this way to avoid circular dependencies. It would be preferable to define it as When(VAPPR\_Selected = Active).

![](images/96e48d9c52ecb84f4eadce1bbadfbef5e380be216c053fedbedc4c74147f363f.jpg)  
Purpose: This variable maintains the current base state of Vertical Approach mode, i.e., whether it is cleared or selected. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

## VAPPR\_Selected

![](images/273f4b00db3e1237a37ee3957d0893f98833f69d7b746286bccdacf3b1b814ee.jpg)

Purpose: This variable maintains the current state of Vertical Approach mode when it is selected, i.e., whether it is armed or active. Note that if this side of the FGS is not active, it obtains its value from the off side. The normal transitions occur only when this side is active.

## 2.7.2.7 Vertical Go Around (VGA) Mode

Go Around mode provides guidance to the pilot after aborting an approach. The AP is never engaged during Go Around mode. Vertical Go Around mode provides guidance to maintain a fixed pitch angle.

<table><tr><td>Definitions of Values to be Imported</td></tr><tr><td></td></tr><tr><td>MACRO</td></tr><tr><td>Select_VGA</td></tr></table>

## Condition:

<table><tr><td>A N</td><td>When_GA_Switch_Pressed_Seenm-116()</td><td>T</td></tr><tr><td>D</td><td>Overspeed_Conditionm-128()</td><td>F</td></tr></table>

Purpose: This event defines when Vertical Go Around mode is to be selected.

<table><tr><td>MACRO</td><td></td></tr><tr><td colspan="2"></td></tr><tr><td colspan="2">Deselect_VGA</td></tr></table>

## Condition:

<table><tr><td rowspan=1 colspan=1>When(APv-132 =Engaged)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Nonbasic_Lateral_Mode_Activatedm-35()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Nonbasic_Vertical_Mode_Activatedm-60()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_SYNC_Switch_Pressed_Seenm-117()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_VS_Pitch_Wheel_Rotated_Seenm-110()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_Pilot_Flying-Transferm-29()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When(Modesv-34 =Off)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event defines when Vertical Go Around mode is to be deselected.

Definitions of Values to be Exported

STATE VARIABLE

Is\_VGA\_Selected

Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (VGAv-94 =Selected) if TRUE

Purpose: Indicates if VGA mode is selected.

STATE VARIABLE

Is\_VGA\_Active  
Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: CONTROLLED   
:= (VGAy-94 =Selected) if TRUE

Purpose: Indicates if VGA mode is active.

Comment: Even though VGA Selected and VGA Active are the same value, this is defined to provide a common set of controlled variables across all modes.

## When\_VGA\_Activated

## Condition:

<table><tr><td rowspan=3 colspan=1>AND</td><td rowspan=1 colspan=1> $\mathrm { S e l e c t . V G A _ { m - 9 1 } ( ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { P R E V I O U S ~ S T E P } ( \mathrm { V G A } _ { \mathrm { v } - 9 4 } ) = \mathrm { S e l e c t e d }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { I s \mathrm { . } T h i s \mathrm { . } S i d e \mathrm { . } A c t i v e _ { v - 3 0 } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This signal occurs when Vertical Go Around mode is activated.

Comment: This event is defined this way to avoid circular dependencies. It would be preferable to define it as When(LGA = Selected).

![](images/cc9983c3893b72ea61f90f612473f2ff9172f76c7245c190310b463fe3c1f2f2.jpg)

## 2.8 Flight Control Laws

The Flight Control Laws generate the pitch and roll guidance commands provided to the Flight Director and the Autopilot. Different Flight Control Laws are armed or activated based on the current modes of the FGS. They also provide inputs to the mode logic that determine when transitions are made from the armed to the active state. While the Flight Control Laws are not specified in this model, this component defines the interface between them and the mode logic and defines the events provided by the Flight Control Laws that the mode logic depends upon. As with events provided by the Flight Control Panel, some of these are prioritized so that if multiple events occur at the same time, only the most significant events are seen by the other parts of the specification.

Definitions of Values to be Exported

MACRO

## When\_NAV\_Track\_Cond\_Met

Condition: Is\_NAV\_Track\_Cond\_Metiv-100

Purpose: This event indicates when the NAV Track Condition is met.

Comment: This is redefined as a macro to simplify verification.

MACRO

When\_NAV\_Track\_Cond\_Met\_Seen

## Condition:

![](images/53dbc1bc216dec2c9c0af238e31d55cc544b70a21e1f029b8fd5e8feeabefa87.jpg)

When\_NAV\_Track\_Cond\_Metm-95()

No\_Higher\_Event\_Than\_NAV\_Track\_Cond\_Metm-96()

Purpose: This event indicates when the NAV Track condition is met and no higher priority event has occurred.

## No\_Higher\_Event\_Than\_NAV\_Track\_Cond\_Met

## Condition:

![](images/8691c6dea50f3965bad2141b63b8ca875f49c2314d901f99a8a8e7415873d1e9.jpg)

When\_FD\_Switch\_Pressedm-103()

No\_Higher\_Event\_Than\_FD\_Switch\_Pressedm-104()

![](images/707d2f4d90456c0b0d44b1d4b424c59ad1689987e98f3b75f2506a0915d1f7b9.jpg)

Purpose: This event occurs when no event with a priority higher than pressing the NAV switch has occurred.

MACRO

When\_ALTSEL\_Track\_Cond\_Met

Condition: Is\_ALTSEL\_Track\_Cond\_Metiv-101

Purpose: This event indicates when the ALTSEL Track Condition is met.

Comment: This is redefined as a macro to simplify verification.

MACRO

When\_ALTSEL\_Track\_Cond\_Met\_Seen

## Condition:

![](images/6c051901b33383850ddae6553a2b4810c74a090cef635fdde2227bcc29564981.jpg)

When\_ALTSEL\_Track\_Cond. $\mathrm { { M e t } _ { \mathrm { { m } - 9 6 } } ( ) }$

D [No\_Higher\_Event\_Than\_ALTSEL\_Track\_Cond. $\mathrm { M e t _ { \mathrm { m - 9 7 } } ( ) }$

![](images/9ee04c93960ead9da6c59f67f97c0ee49af50bdf78f3bfde07c1274b04eb58fb.jpg)

Purpose: This event indicates when the ALTSEL Track condition is met and no higher priority event has occurred.

MACRO

## No\_Higher\_Event\_Than\_ALTSEL\_Track\_Cond\_Met

## Condition:

![](images/43ececffa91627fab97c7bd3922ee325eedcb5f54cc2627d44b86073a6cf7875.jpg)

|When\_FD\_Switch\_Pressedm-103()

No\_Higher\_Event\_Than\_FD\_Switch\_Pressedm-104()

![](images/48b773eb5d99bcb9a73c7858b81bf7ba6748a572792fe553c0b7e827ddea5cc0.jpg)

Purpose: This event occurs when no event with a priority higher than pressing the FD switch has occurred.

MACRO

When\_ALTSEL\_Capture\_Cond\_Met

Condition: Is\_ALTSEL\_Capture\_Cond\_Metiv-101

Purpose: This event indicates when the ALTSEL Capture Condition is met.

Comment: This is redefined as a macro to simplify verification.

MACRO

When\_ALTSEL\_Capture\_Cond\_Met\_Seen

## Condition:

![](images/597a41fff82fa8fbd26148308cd863851c32248bbad044c971092753768c4b5b.jpg)

When\_ALTSEL\_Capture\_Cond\_Metm-97()

No\_Higher\_Event\_Than\_ALTSEL\_Capture\_Cond. $\mathrm { { M e t } _ { \mathrm { { m } - 9 8 } } ( ) }$

![](images/0ac81bf4ee1f323c0bd075688bc1c8b3752eba557ad5f28a6d142e700cdb91ad.jpg)

Purpose: This event indicates when the ALTSEL Capture condition is met and no higher priority event has occurred.

MACRO

## No\_Higher\_Event\_Than\_ALTSEL\_Capture\_Cond\_Met

## Condition:

![](images/1fc9385f7e539e449457a3b73ff899571def8686ce2507f8f7a2590c2a15f06a.jpg)

When\_FD\_Switch\_Pressedm-103()

No\_Higher\_Event\_Than\_FD\_Switch\_Pressedm-104()

![](images/e2752b5bea705809b3e4aa6cdf666499abbc22f85ac6d678c4a84fefe2ed6cc0.jpg)

Purpose: This event occurs when no event with a priority higher than pressing the FD switch has occurred.

MACRO

When\_LAPPR\_Track\_Cond\_Met

Condition: Is\_LAPPR\_Track\_Cond\_Metiv-101

Purpose: This event indicates when the LAPPR Track Condition is met.

Comment: This is redefined as a macro to simplify verification.

MACRO

When\_LAPPR\_Track\_Cond\_Met\_Seen

## Condition:

![](images/71afd419a7c8f314eb9dbb748e940241e280e4fd4dbb023ec466aefe4cca5662.jpg)

When\_LAPPR\_Track\_Cond\_Metm-98()

No\_Higher\_Event\_Than\_LAPPR\_Track\_Cond\_Metm-99()

![](images/b91fb4ff02826beb8a8c1e38b2b520e923e40ae4c54da2801c09f3f7962649ea.jpg)

Purpose: This event indicates when the LAPPR Track condition is met and no higher priority event has occurred.

![](images/882e744de23ce7f434cb00ac36931377399ea18d1413373d78c5f32e04769282.jpg)

## No\_Higher\_Event\_Than\_LAPPR\_Track\_Cond\_Met

## Condition:

![](images/9b87ad4b3ae653938d5701e72b0ceefe6c0221a9119821bb9a5d07feb4bfe10a.jpg)

When\_FD\_Switch\_Pressedm-103()

No\_Higher\_Event\_Than\_FD\_Switch\_Pressedm-104()

Purpose: This event occurs when no event with a priority higher than pressing the FD switch has occurred.

MACRO

## When\_VAPPR\_Track\_Cond\_Met

Condition: Is\_VAPPR\_Track\_Cond\_Metiv-102

Purpose: This event indicates when the VAPPR Track Condition is met.

Comment: This is redefined as a macro to simplify verification.

MACRO

When\_VAPPR\_Track\_Cond\_Met\_Seen

## Condition:

When\_VAPPR\_Track\_Cond\_Metm-99()

[No\_Higher\_Event\_Than\_VAPPR\_Track\_Cond\_Metm-100()

![](images/29a9718ae9f17df7eb4d4e7eec005a032f5a62edc75a11d6833e419019c61cb4.jpg)

Purpose: This event indicates when the VAPPR Track condition is met and no higher priority event has occurred.

## No\_Higher\_Event\_Than\_VAPPR\_Track\_Cond\_Met

## Condition:

<table><tr><td>AN</td><td>When_FD_Switch_Pressedm-103()</td><td>F</td></tr><tr><td>D</td><td>No_Higher_Event_Than_FD_Switch_Pressedm-104()</td><td>T</td></tr></table>

Purpose: This event occurs when no event with a priority higher than pressing the FD switch has occurred.

Definitions of Values to be Encapsulated

INPUT VARIABLE

Is\_NAV\_Track\_Cond\_Met

Type: BOOLEAN

Initial Value: FALSE

Classified as: MONITORED

Purpose: This input variable becomes true when the lateral navigation (NAV) flight control law transitions from the armed to the track state.

# Is\_ALTSEL\_Capture\_Cond\_Met

Type: BOOLEAN

Initial Value: FALSE

Classified as: MONITORED

Purpose: This input variable becomes true when the vertical altitude select flight control law transitions from the armed to the capture state.

INPUT VARIABLE

## Is\_ALTSEL\_Track\_Cond\_Met

Type: BOOLEAN

Initial Value: FALSE

Classified as: MONITORED

Purpose: This input variable becomes true when the vertical altitude select flight control law transitions from the capture to the track state.

INPUT VARIABLE

## Is\_LAPPR\_Track\_Cond\_Met

Type: BOOLEAN

Initial Value: FALSE

Classified as: MONITORED

Purpose: This input variable becomes true when the lateral approach (LAPPR) flight control law transitions from the armed to the track state.

# Is\_VAPPR\_Track\_Cond\_Met

Type: BOOLEAN

Initial Value: FALSE

Classified as: MONITORED

Purpose: This input variable becomes true when the vertical approach (VAPPR) flight control law transitions from the armed to the track state.

<table><tr><td rowspan=1 colspan=1>When_FD_Switch_Pressedm-103()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>No_Higher_Event_Than_FD_Switch_Pressedm-104()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

## 2.9 Flight Control Panel (FCP)

The Flight Control Panel (FCP) is the primary device with which the flight crew interacts with the FGS. This component defines the FGS's view of the FCP. This consists of the definition of the monitored variables representing the switches and dials of the FCP and the controlled variables representing the lamps displayed on the FCP. A few additional inputs, such as the SYNC and AP Disengage switches on the control yokes and the GA switches on the throttles, are routed through the FCP aand are defined here. This component also defines FCP specific events, such as the pressing of a switch, used in the rest of the specification. These events are prioritized so that if multiple events occur at the same time, only the most significant events are seen by the other parts of the specification.

Definitions of Values to be Exported

MACRO

When\_FD\_Switch\_Pressed

Condition: When(FD\_Switchiv-118 =ON)

Purpose: This event indicates when theFD switch associated with this FGS is pressed.

Comment: This is redefined as a macro to simplify verification.

MACRO

When\_FD\_Switch\_Pressed\_Seen

## Condition:

Purpose: This event occurs when the FD Switch is pressed and no higher priority event has occurred.

MACRO

## No\_Higher\_Event\_Than\_FD\_Switch\_Pressed

## Condition:

![](images/27889e8d7e438f0a303c8493f5045739c3ed340de998e0573136d9f9b45e6276.jpg)

When\_Transfer\_Switch\_Pressedm-104()

[No\_Higher\_Event\_Than\_Transfer\_Switch\_Pressedm-105()

![](images/89df2518dc5ca00845ca4a6e5efca70e408f37f2023dd975317a18726cb64ca5.jpg)

Purpose: This event occurs when no event with a priority higher than pressingthe FD switch has occurred.

MACRO

When\_Transfer\_Switch\_Pressed

Condition: When(Transfer\_Switchiv-125 =ON)

Purpose: This event indicates when the TRANSFER switch ais pressed.

Comment: This is redefined as a macro to simplify verification.

MACRO

When\_Transfer\_Switch\_Pressed\_Seen

## Condition:

![](images/902e94659af41f8fd338287f7e0d7d72bedb397e2b3d5bac36c9e43af4488738.jpg)

[When\_Transfer\_Switch\_Pressedm-104()

D [No\_Higher\_Event\_Than\_Transfer\_Switch\_Pressedm-105()

![](images/8cce5823e6736331247162de59051ea223cbba4db1cf6dcaa988d6ac80791b79.jpg)

Purpose: This event indicates when the Transfer switch is pressed and no higher priority event has occurred.

## No\_Higher\_Event\_Than\_Transfer\_Switch\_Pressed

## Condition:

![](images/32825034b350f60f80e70076d2b7579bfd2ca3ee7adc728d922749b239b19cab.jpg)

<table><tr><td rowspan=1 colspan=1>When_AP_Engage_Switch_Pressedm-105()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1>No_Higher_Event_Than_AP_Engage_Switch_Pressedm-106()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>When_VS_Pitch_Wheel_Rotatedm-109()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1>No_Higher_Event_Than_VS_Pitch_Wheel_Rotatedm-110()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr><tr><td rowspan=1 colspan=1>When_NAV_Switch_Pressedm-107()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>F</td></tr><tr><td rowspan=1 colspan=1>No_Higher_Event_Than_NAV_Switch_Pressedm-108()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

Purpose: This event occurs when no event with a priority higher than pressing the Transfer switch has occurred.

MACRO

When\_AP\_Engage\_Switch\_Pressed

Condition: When(AP\_Engage. $\mathrm { S w i t c h } _ { \mathrm { i v - } 1 2 6 } = \mathrm { O N } )$

Purpose: This event indicates when the AP Engaged switch is pressed.

Comment: This is redefined as a macro to simplify verification.

MACRO

## When\_AP\_Engage\_Switch\_Pressed\_Seen

## Condition:

![](images/4b4d119e5b8e1b616308a44b1404f1b9066972bd54655083883b323deadcde5e.jpg)

When\_AP\_Engage\_Switch\_Pressedm-105()

No\_Higher\_Event\_Than\_AP\_Engage\_Switch\_Pressedm-106()

![](images/a35b6110fed45d54042dbd6a4aadc0d53f5e9a6d5efad51a7aee597278bb67b6.jpg)

Purpose: This event indicates when the AP Engage switch is pressed and no higher priority event has occurred.

MACRO

No\_Higher\_Event\_Than\_AP\_Engage\_Switch\_Pressed

## Condition:

![](images/deedf65645251af8f5bec0fe196dd0d486ea92e8023b2314a0b02b9bb91f13e9.jpg)

When\_AP\_Disconnect\_Switch\_Pressedm-106()

No\_Higher\_Event\_Than\_AP\_Disconnect\_Switch\_Pressedm-107()

![](images/6b39c21213ba0349c31c2c6d9bbdb137a87b8489ece2e72b5c054df9983d28cf.jpg)

Purpose: This event occurs when no event with a priority higher than pressing the AP Engage switch has occurred.

MACRO

When\_AP\_Disconnect\_Switch\_Pressed

Condition: When(AP\_Disconnect\_Switchiv-126 =ON)

Purpose: This event indicates when the AP Disconnect switch is pressed.

Comment: This is redefined as a macro to simplify verification.

## When\_AP\_Disconnect\_Switch\_Pressed\_Seen

## Condition:

![](images/b02794f0792ec6d541b03d4ecd33a01c8910375a98367f9f89c9ad31a31da1d5.jpg)

When\_AP\_Disconnect\_Switch\_Pressedm-106()

D No\_Higher\_Event\_Than\_AP\_Disconnect\_Switch\_Pressedm-107()

![](images/d97e43cb7c94ac696e9ee10ad9512f355e3873c930e4eabf7a0815929cff6635.jpg)

Purpose: This event indicates when the AP Disconnect switch is pressed and no higher priority event has occurred.

MACRO

## No\_Higher\_Event\_Than\_AP\_Disconnect\_Switch\_Pressed

Condition: TRUE

Purpose: This event occurs when no event with a priority higher than pressing the AP Disconnect switch has occurred.

Lateral Switches

MACRO

When\_NAV\_Switch\_Pressed

Condition: When(NAV\_Switchiv-119 =ON)

Purpose: This event indicates when the NAV switch is pressed.

Comment: This is redefined as a macro to simplify verification.

## When\_NAV\_Switch\_Pressed\_Seen

## Condition:

![](images/2520b952900badb0e5a9693a3fcb43a7b9e2dd61c9ea8bdda7fd0f6b0386a6cf.jpg)

When\_NAV\_Switch\_Pressedm-107()

No\_Higher\_Event\_Than\_NAV\_Switch\_Pressedm-108()

![](images/566406cdb838f83af8031e2883ce12e0cb441e7fa106de5b1120bf70a8adb8c5.jpg)

Purpose: This event indicates when the NAV Switch is pressed and no higher priority event has occurred.

MACRO

No\_Higher\_Event\_ThanNAV\_Switch\_Pressed

## Condition:

![](images/8f495085f22a9c1cd350315b93f5f0305300cb09decf1507c6e33d8d42c2d18e.jpg)

When\_HDG\_Switch\_Pressedm-108()

No\_Higher\_Event\_Than\_HDG\_Switch\_Pressedm-109()

![](images/3c412dd5d4b4bf0c21e7c8516674dcb4e7033b79414a7e142fdbfec7395f2ded.jpg)

Purpose: This event occurs when no event with a priority higher than pressing the NAV switch has occurred.

MACRO

When\_HDG\_Switch\_Pressed

Condition: When(HDG\_Switchiv-118 =ON)

Purpose: This event indicates when the HDG switch is pressed.

Comment: This is redefined as a macro to simplify verification.

## When\_HDG\_Switch\_Pressed\_Seen

## Condition:

![](images/20aa65ab6573006d7791e6009950c7b5cbfa1fefafeab761cbd27aae0259d6a0.jpg)

When\_HDG\_Switch\_Pressedm-108()

No\_Higher\_Event\_Than\_HDG\_Switch\_Pressedm-109()

![](images/9625b5a48bfa6454c6685cf8abb0cbfad67358888bffa629fdd6aaaea7a8e9c9.jpg)

Purpose: This event indicates when the NAV Switch is pressed and no higher priority event has occurred.

MACRO

No\_Higher\_Event\_Than\_HDG\_Switch\_Pressed

## Condition:

![](images/67350427db9b4104053c3accb56e70055fd218f19e2b51f52867708593df81b2.jpg)

[No\_Higher\_Event\_Than\_APPR\_Switch\_Pressedm-115()

When\_APPR\_Switch\_Pressedm-114()

![](images/88eb3c4c1048d48d9597c362a3764bc07e91955b0b6057b2daea3f46e09e5dbf.jpg)

Purpose: This event occurs when no event with a priority higher than pressing the HDG switch has occurred.

Vertical Switches

MACRO

When\_VS\_Pitch\_Wheel\_Rotated

Condition: When(VS\_Pitch\_Wheel\_In\_Motioniv-125)

Purpose: This event indicates when the VS Pitch Wheel is rotated.

MACRO

# When\_VS\_Pitch\_Wheel\_Rotated\_Seen

## Condition:

![](images/59620ee973ae3b385af045e455124e79b0330f6d503527bb648da47d898d8f10.jpg)

When\_VS\_Pitch\_Wheel\_Rotatedm-109()

No\_Higher\_Event\_Than\_VS\_Pitch\_Wheel\_Rotatedm-110()

![](images/b786ffd79b62ea04d1401e175dc43e12263d4cd0d6c8f1817cb674b04f7d76f1.jpg)

Purpose: This event indicates when the VS Pitch Wheel is rotated and no higher priority event has occurred.

MACRO

## No\_Higher\_Event\_Than\_VS\_Pitch\_Wheel\_Rotated

## Condition:

![](images/5eae32a6027312cdf70052d6cd2795fa0ef8c47bb4e354fb038174799ca52ea0.jpg)

When\_VS\_Switch\_Pressedm-110()

D |No\_Higher\_Event\_Than\_VS\_Switch\_Pressedm-111()

![](images/ba3d404f7429dc0309281566cce09da1c1e0616193cdeea8311435c48b62c1e3.jpg)

Purpose: This event occurs when no event with a priority higher than rotating the VS Pitch Wheel has occurred.

MACRO

When\_VS\_Switch\_Pressed

Condition: When(VS\_Switchiv-120=ON)

Purpose: This event indicates when the VS switch is pressed.

Comment: This is redefined as a macro to simplify verification.

MACRO

When\_VS\_Switch\_Pressed\_Seen

## Condition:

![](images/7b50fc7e837b7aec67ef5823d8b2b7d1db1c18d1fde471a9f47e31bdc77ebaa9.jpg)

When\_VS\_Switch\_Pressedm-110()

D No\_Higher\_Event\_Than\_VS\_Switch\_Pressedm-111()

![](images/4f2d6ece46679fdf869b793e1643b2859f6aafdbeb36d70172b3450333c2d237.jpg)

Purpose: This event indicates when the VS switch pressed and no higher priority event has occurred.

MACRO

No\_Higher\_Event\_Than\_VS\_Switch\_Pressed

## Condition:

![](images/808bb609b8c2206e07f0baeb2b92a75195c30c79c135745637894267828d56f6.jpg)

When\_FLC\_Switch\_Pressedm-111()

D [No\_Higher\_Event\_Than\_FLC\_Switch\_Pressedm-112()

![](images/6a7a824a6e28a5b95c40f1d0c920ecad5a5fc9bad15500a54490dcd4258f1dfa.jpg)

Purpose: This event occurs when no event with a priority higher than pressing the VS switch has occurred.

MACRO

When\_FLC\_Switch\_Pressed

Condition: When(FLC\_Switchiv-122 =ON)

Purpose: This event indicates when the FLC switch is pressed.

Comment: This is redefined as a macro to simplify verification.

MACRO

## When\_FLC\_Switch\_Pressed\_Seen

## Condition:

![](images/6642cb541a5761704ec8949a0b0f86194f0ce495420ec0b8e553a127722e9c06.jpg)

When\_FLC\_Switch\_Pressedm-111()

No\_Higher\_Event\_Than\_FLC\_Switch\_Pressedm-112()

![](images/b911e71bf3972503ade0e2fc285a860f9f4955ec209a0ee7e9fe8362ec20f1f1.jpg)

Purpose: This event indicates when the FLC switch pressed and no higher priority event has occurred.

MACRO

## No\_Higher\_Event\_Than\_FLC\_Switch\_Pressed

## Condition:

![](images/bbc5df2a77388df03d0e22ec38c384029b6230d210f2e9404a0be64fb4bb1cdb.jpg)

When\_ALT\_Switch\_Pressedm-112()

No\_Higher\_Event\_Than\_ALT\_Switch\_Pressedm-113()

![](images/3bd0efba0b17c253d3757d0cf9a0c6f2c68fcff349235e14452bc03af96f6306.jpg)

Purpose: This event occurs when no event with a priority higher than pressing the FLC switch has occurred.

MACRO

When\_ALT\_Switch\_Pressed

Condition: When(ALT\_Switchiv-121 =ON)

Purpose: This event indicates when the ALT switch is pressed.

Comment: This is redefined as a macro to simplify verification.

MACRO

When\_ALT\_Switch\_Pressed\_Seen

## Condition:

![](images/37981a8f82215cbe4dded68df9ed08df5651fff7ea7d93d37bb932f8758defca.jpg)

When\_ALT\_Switch\_Pressedm-112()

No\_Higher\_Event\_Than\_ALT\_Switch\_Pressedm-113()

![](images/4c0ebe5d87075a92db5d8e6f987e9b6cf8fe06d4d16b0192e3b4a724df23a0ff.jpg)

Purpose: This event indicates when the ALT switch pressed and no higher priority event has occurred.

MACRO

No\_Higher\_Event\_Than\_ALT\_Switch\_Pressed

## Condition:

![](images/3df7a7d3a0516ecc7907a21ae5b75af30ef527959528264166b504ba706c5778.jpg)

When\_ALTSEL\_Target\_Altitude\_Changedm-113()

No\_Higher\_Event\_Than\_ALTSEL\_Target\_Altitude\_Changedm-114()

![](images/a18914af57aff68a8b2e14c6d449a2dddfe7a4df316ce30bf9f9fc31ba5fde89.jpg)

Purpose: This event occurs when no event with a priority higher than pressing the ALT switch has occurred.

MACRO

When\_ALTSEL\_Target\_Altitude\_Changed

## Condition:

![](images/ae547664c2a8c192f325dbed2c8136fe2449b4dec621ba02e22db782544e2e07.jpg)

ALTSEL\_Target\_Altitude\_Changediv-129 =UNDEFINED

ALTSEL\_Target\_Altitude\_Changediv-129

![](images/e9b8b2432824bd8fbfc20919ff9b9c7fae2090fb21db48e2b69983f0e1d6ae6a.jpg)

Purpose: This event indicates when the ALTSEL target altitude is changed.

MACRO

## When\_ALTSEL\_Target\_Altitude\_Changed\_Seen

## Condition:

![](images/4972d928a9f7f2f71e688183e25e71e61dc8744734471057bbfef37f2b671a1e.jpg)

When\_ALTSEL\_Target\_Altitude\_Changedm-113()

[No\_Higher\_Event\_Than\_ALTSEL\_Target\_Altitude\_Changedm-114()

![](images/360dea04d2e9f2e37e79e9b7ae115637cc17fb4f4777d98e75532bc0777ee5bc.jpg)

Purpose: This event indicates when the ALTSEL target altitude is changed and no higher priority event has occurred.

MACRO

## No\_Higher\_Event\_Than\_ALTSEL\_Target\_Altitude\_Changed

## Condition:

![](images/ee68e8210bff5dbbeb75a51bf30896a596aaa76c69a08e00aae693d0abc81479.jpg)

When\_APPR\_Switch\_Pressedm-114()

[No\_Higher\_Event\_Than\_APPR\_Switch\_Pressedm-115()

![](images/a3d694fd3a11c37e42a7b92e4f1ae0fc8904c9873e5f891df23c49a92f1d9367.jpg)

Purpose: This event occurs when no event with a priority higher than rotating the changing of the ALTSEL target altitude has occurred.

Lateral and Vertical Events

MACRO

When\_APPR\_Switch\_Pressed

Condition: When(APPR\_Switchiv-123 =ON)

Purpose: This event indicates when the APPR switch is pressed.

Comment: This is redefined as a macro to simplify verification.

When\_APPR\_Switch\_Pressed\_Seen

## Condition:

![](images/2bb51679dc8662a3f7a3c237e25b64a6ab8509586db2e5c154b9470a6df0b225.jpg)

When\_APPR\_Switch\_Pressedm-114()

D [No\_Higher\_Event\_Than\_APPR\_Switch\_Pressedm-115()

![](images/66227ada9a6b39d762f207d867ec9df51749314d84a6bcf801bfe775cd5ff5c9.jpg)

Purpose: This event indicates when the APPR switch pressed and no higher priority event has occurred.

MACRO

No\_Higher\_Event\_Than\_APPR\_Switch\_Pressed

## Condition:

![](images/4cc921e159640426952cf55426bf181d5dbd0b1cbd98650af2b1b0573dd32775.jpg)

When\_GA\_Switch\_Pressedm-115()

D [No\_Higher\_Event\_Than\_GA\_Switch\_Pressedm-116()

![](images/0db297c758a281512e440072c10882bbc9e70d9fdeaf19321d5aff0aa0578679.jpg)

Purpose: This event occurs when no event with a priority higher than pressing the APPR switch has occurred.

MACRO

When\_GA\_Switch\_Pressed

Condition: When(GA\_Switchiv-124 =ON)

Purpose: This event indicates when the GA switch is pressed.

Comment: This is redefined as a macro to simplify verification.

MACRO

## When\_GA\_Switch\_Pressed\_Seen

## Condition:

![](images/300b2db8978c9e0e880d82f09bb8d1f26dd80d2ae3054f345cde5415a725e770.jpg)

When\_GA\_Switch\_Pressedm-115()

No\_Higher\_Event\_Than\_GA\_Switch\_Pressedm-116()

![](images/b9963040a491a6d422f02b8fe7239f23d666c4677f42e7acda98fe61f3cfc2fc.jpg)

Purpose: This event indicates when the GA switch pressed and no higher priority event has occurred.

MACRO

No\_Higher\_Event\_Than\_GA\_Switch\_Pressed

## Condition:

![](images/a077470fccb0e374914643c7c670266e9a844fd08e3d87b887412e1f0a2a8474.jpg)

When\_SYNC\_Switch\_Pressedm-116()

No\_Higher\_Event\_Than\_SYNC\_Switch\_Pressedm-117()

![](images/3611613a241691a6a72f7be52c6cb5132e7e0616ce316b8b58af57ecbd242bc1.jpg)

Purpose: This event occurs when no event with a priority higher than pressing the GA switch has occurred.

MACRO

When\_SYNC\_Switch\_Pressed

Condition: When(SYNC\_Switchiv-125 =ON)

Purpose: This event indicates when the SYNC switch is pressed.

Comment: This is redefined as a macro to simplify verification.

![](images/cedc8c5372b77b88545fe08828ffe5cbf23bd81ffdba49701c3d2bc02370fe42.jpg)

## When\_SYNC\_Switch\_Pressed\_Seen

## Condition:

![](images/a1db7f33b248b7a4db37904d903a1c11cecd088ac3af904121a142f42645b5ae.jpg)

When\_SYNC\_Switch\_Pressedm-116()

D [No\_Higher\_Event\_Than\_SYNC\_Switch\_Pressedm-117()

Purpose: This event indicates when the SYNC switch pressed and no higher priority event has occurred.

MACRO

No\_Higher\_Event\_Than\_SYNC\_Switch\_Pressed

Condition: TRUE

Purpose: This event occurs when no event with a priority higher than pressing the GA switch has occurred.

Definitions of Values to be Encapsulated

TYPE

Switch

Possible Values: OFF, ON

<table><tr><td></td><td>TYPE</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td>Lamp</td><td></td></tr></table>

Possible Values: OFF, ON

<table><tr><td></td><td>INPUT VARIABLE</td><td></td></tr><tr><td></td><td>FD_Switch</td><td></td></tr></table>

Type: {OFF, ON}ty-117

Initial Value: UNDEFINED

Classified as: MONITORED

Purpose: Holds the last sensed position of the FD switch associated with this FGS.

<table><tr><td></td><td>INPUT VARIABLE</td></tr><tr><td></td><td>HDG_Switch</td></tr></table>

Type: {OFF, ON}ty-117

Initial Value: UNDEFINED

Classified as: MONITORED

Purpose: Holds the last sensed position of the HDG switch.

Parent: NONE

Type: {OFF, ON}ty-118

Initial Value: OFF

Classified as: CONTROLLED

:= OFF if not Is\_HDG\_Selectedv-41

Purpose: Indicates if the HDG switch lamp on the FCP should be on or off.

INPUT VARIABLE

## NAV\_Switch

Type: {OFF, ON}ty-117

Initial Value: UNDEFINED

Classified as: MONITORED

Purpose: Holds the last sensed position of the NAV switch.

# NAV\_Lamp

Parent:NoNE

Type: {OFF, ON}ty-118

:= OFF if not Is\_NAV\_Selectedv-46

Purpose: Indicates if the NAV switch lamp should be on or off.

INPUT VARIABLE

VS\_Switch

Type: {OFF, ON}ty-117

Initial Value: UNDEFINED

Classified as: MONITORED

Purpose: Holds the last sensed position of the VS switch.

STATE VARIABLE

Parent: NoNE

:= OFF if not Is\_VS\_Selectedv-66

Purpose: Indicates if the VS switch lamp should be on or off.

INPUT VARIABLE

ALT\_Switch

Type: {OFF, ON}ty-117

Initial Value: UNDEFINED

Classified as: MONITORED

Purpose: Holds the last sensed position of the ALT switch.

## ALT\_Lamp

Parent: NONE

Type: {OFF, ON}ty-118

Initial Value: OFF

Classified as: CONTROLLED

:= ON if Is\_ALT\_Selectedy-74

:= OFF if not Is\_ALT\_Selectedv-74

Purpose: Indicates if the ALT switch lamp should be on or off.

INPUT VARIABLE

FLC\_Switch

Type: {OFF, ON}ty-117

Initial Value: UNDEFINED

Classified as: MONITORED

Purpose: Holds the last sensed position of the FLC switch.

FLC\_Lamp

Parent: NONE

Type: {OFF, ON}ty-118

Initial Value: OFF

Classified as: CONTROLLED

:= OFF if not Is\_FLC\_Selectedv-70

Purpose: Indicates if the FLC switch lamp should be on or off.

INPUT VARIABLE

## APPR\_Switch

Type: {OFF, ON}ty-117

Initial Value: UNDEFINED

Classified as: MONITORED

Purpose: Holds the last sensed position of the APPR switch.

Classified as: MONITORED

![](images/5e4c10ee11bf039db0c56760f42e7c6ad29ac37a4ec5ea58a7f00cb9014cd516.jpg)  
Purpose: Indicates if the APPR switch lamp should be on or off.  
Initial Value: UNDEFINED  
Purpose: Holds the last sensed position of the GA switch.

INPUT VARIABLE

## SYNC\_Switch

Type: {OFF, ON}ty-117

Initial Value: UNDEFINED

Classified as: MONITORED

Purpose: Holds the last sensed position of the SYNC switch.

INPUT VARIABLE

Transfer\_Switch

Type: {OFF, ON}ty-117

Initial Value: UNDEFINED

Classified as: MONITORED

Purpose: Holds the last sensed position of the TRANSFER switch.

INPUT VARIABLE

## VS\_Pitch\_Wheel\_In\_Motion

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: MONITORED

Purpose: Holds the last sensed position of the VS/Pitch wheel.

## AP\_Engage\_Switch

Type: {OFF, ON}ty-117

Initial Value: UNDEFINED

Classified as: MONITORED

Purpose: Holds the last sensed position of the AP Engage switch.

STATE VARIABLE

Purpose: Indicates if the AP switch lamp should be on or off.

INPUT VARIABLE

AP\_Disconnect\_Switch

Type: {OFF, ON}ty-117

Initial Value: UNDEFINED

Classified as: MONITORED

Purpose: Holds the last sensed position of the AP Disconnect switch.

## 2.10 Navigation Sources

The FGS receives navigation information from several sources, including VHF Omni-Directional Range (VOR) for lateral navigation, Localizer (LOC) for precision lateral approach, and Glideslope (GS) for precision vertical approach. This component defines the FGS's view of its navigation sources. This includes definition of the types of sources available, the currently selected source, and the information available from that source.

Definitions of Values to be Exported

STATE VARIABLE

When\_Selected\_Nav\_Source\_Changed

Parent: NoNE

Type: BOOLEAN

Initial Value: FALSE

Classified as: MONITORED

Purpose: This event occurs when a new navigation source is selected.

STATE VARIABLE

When\_Selected\_Nav\_Frequency\_Changed

Parent: NONE

Type: BOOLEAN

Initial Value: FALSE

Classified as: MONITORED

Purpose: This event occurs when the frequency of the selected navigation source is changed.

## 2.11 Air Data System

The Air Data System provides information about the aircraft state sensed from the surrounding air mass such as whether an overspeed condition exists. This component defines the FGS's view of the Air Data System

<table><tr><td colspan="2">Definitions of Values to be Exported</td></tr><tr><td colspan="2"></td></tr><tr><td rowspan="2"></td><td></td></tr><tr><td>MACRO</td></tr><tr><td colspan="2">Overspeed_Condition</td></tr></table>

Condition:

Overspeediv-128 ≠UNDEFINED

Definitions of Values to be Encapsulated

INPUT VARIABLE

Overspeed

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: MONITORED

Purpose: This state variable indicates if an overspeed condition exists.

## 2.12 References

References refer to target values used by several of the modes, such as the Preselected Altitude. These may be set by the flight crew through the Flight Control Panel, or set to the current aircraft value on entry to a mode or a synchronization request. The references may be physically maintained by a variety of systems. This component defines the FGS's view of the references. Details of how these values are obtained from other systems are encapsulated within this component.

Definitions of Values to be Exported

INPUT VARIABLE

## ALTSEL\_Target\_Altitude\_Changed

Type: BOOLEAN

Initial Value: TRUE

Classified as: MONITORED

Purpose: This input variable holds the most recent information on whether the ALTSEL target altitude (either the PSA or FPTA) has been changed.

## 2.13 Autopilot (AP)

The Autopilot (AP) commands movement of the control surfaces based on the pitch and roll commands generated by the FGS. This component defines the FGS's view of the AP.

<table><tr><td>Definitions of Values to be Imported</td></tr><tr><td></td></tr><tr><td>MACRO</td></tr><tr><td></td></tr></table>

Condition: When\_AP\_Engage\_Switch\_Pressed\_Seenm-106()

Purpose: This event defines when the AP is to be engaged.

MACRO

When\_Disengage\_AP

## Condition:

<table><tr><td rowspan=1 colspan=1>When_AP_Engage_Switch_Pressed_Seenm-106()</td><td rowspan=1 colspan=2>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>When_AP_Disconnect_Switch_Pressed_Seenm-107()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1><img src="images/75860f7509fca6bb415d6419e39a07a3e28dd2c3d708a88f7019329ba74a1497.jpg"/></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=3></td></tr></table>

Purpose: This event defines when the AP is to be disengaged.

<table><tr><td colspan="2">Definitions of Values to be Exported</td></tr><tr><td colspan="2"></td></tr><tr><td></td><td>STATE VARIABLE</td></tr><tr><td>Is_AP_Engaged</td><td></td></tr></table>

Purpose: Indicates if the AP is engaged.
<table><tr><td>Definitions of Values to be Encapsulated</td></tr><tr><td></td></tr><tr><td>TYPE</td></tr></table>

Possible Values: Disengaged, Engaged

![](images/6b474f2071df4ffb25a01b8c02c36c559762ed7911c143f006f809c1f12b18ae.jpg)  
Purpose: This variable maintains the current state of the autopilot.

## 2.14 Offside FGS

The FGS has two physical sides, or channels, on the left and right sides of the aircraft. These provide redundant implementations that communicate with each other over a cross-channel bus. This component defines this side of the FGS's view of the other side.

Definitions of Values to be Exported   
STATE VARIABLE   
Offside\_FD   
Parent: NoNE   
Type: {Off, On}ty-23   
Initial Value: Off   
Classified as: MONITORED   
:= Off if not Offside\_FD\_Oniv-145   
:= On if Offside\_FD\_Oniv-145   
Purpose: This variable holds the most recent information on the state of the FD   
on the offside FD.

# Is\_Offside\_LAPPR\_Active

Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: MONITORED   
:= Offside\_LAPPR\_Selectedv-138 =Active if TRUE

Purpose: Indicates if offside LAPPR mode is active.

STATE VARIABLE

Is\_Offside\_VAPPR\_Active  
Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as:MONITORED   
:= Offside\_VAPPR\_Selectedv-143 =Active if TRUE

Purpose: Indicates if offside VAPPR mode is active.

# Is\_Offside\_VGA\_Active

Parent: NoNE   
Type: BOOLEAN   
Initial Value: FALSE   
Classified as: MONITORED   
:= Offside\_VGAv-144 =Selected if TRUE

Purpose: Indicates if offside VGA mode is active.

STATE VARIABLE

Offside\_Modes

Parent: NONE   
Type: {Off, On}ty-23   
Initial Value: Off   
Classified as: MONITORED   
:= Off if not Offside\_Modes\_Oniv-145   
:= On if Offside\_Modes\_Oniv-145

Purpose: This variable holds the most recent information on the state of the mode annunciations on the offside FGS.

Offside\_HDG

Purpose: This variable holds the most recent information on the base state of the lateral ROLL mode of the offside FGS.

STATE VARIABLE

Parent: Offside\_Modesv-135.On

Purpose: This variable holds the most recent information on the base state of the lateral HDG mode of the offside FGS.

Parent: Offside\_Modesv-135.On  Offside\_NAVv-137.Selected   
Type: {Armed, Active}ty-23   
Initial Value: UNDEFINED   
Classified as: MONITORED   
:= Armed if not Offside\_Nav\_Activeiv-146   
:= Active if Offside\_Nav\_Activeiv-146   
Purpose: This variable holds the most recent information on the selected state of   
the lateral NAV mode of the offside FGS.  
Offside\_NAV\_Selected

# Offside\_NAV

Purpose: This variable holds the most recent information on the base state of the lateral NAV mode of the offside FGS.

STATE VARIABLE

Parent: Offside\_Modesv-135.On  Offside\_LAPPRv-138.Selected   
Type: {Armed, Active}ty-23   
Initial Value: UNDEFINED   
Classified as: MONITORED   
:= Armed if not Offside\_Lappr\_Activeiv-147   
:= Active if Offside\_Lappr\_Activeiv-147   
Purpose: This variable holds the most recent information on the selected state of   
the lateral APPR mode of the offside FGS.  
Offside\_LAPPR\_Selected

## Offside\_LAPPR

Purpose: This variable holds the most recent information on the base state of the lateral APPR mode of the offside FGS.

STATE VARIABLE

## Offside\_LGA

Parent: Offside\_Modesy-135.On

Type: {Cleared, Selected}ty-23

Initial Value: UNDEFINED

Classified as: MONITORED

:= Cleared if not Offside\_Lga\_Selectediv-147

:= Selected if Offside\_Lga\_Selectediv-147

Purpose: This variable holds the most recent information on the base state of the lateral GA mode of the offside FGS.

STATE VARIABLE

## Offside\_PITCH

Parent: Offside\_Modesv-135.On

Type: {Cleared, Selected}ty-23

Initial Value: UNDEFINED

Classified as: MONITORED

:= Selected if Offside\_Pitch\_Selectediv-148

Purpose: This variable holds the most recent information on the base state of the vertical PITCH mode of the offside FGS.

Offside\_FLC

Purpose: This variable holds the most recent information on the base state of the vertical VS mode of the offside FGS.

STATE VARIABLE

Purpose: This variable holds the most recent information on the base state of the vertical FLC mode of the offside FGS.

Purpose: This variable holds the most recent information on the base state of the vertical ALT mode of the offside FGS.

STATE VARIABLE

# Offside\_ALTSEL\_Selected

Parent: Offside\_Modesv-135.On  Offside\_ALTSELv-141.Selected

Type: {Armed, Active}ty-23

Initial Value: UNDEFINED

Classified as: MONITORED

:= Armed if not Offside\_Altsel\_Activeiv-149

:= Active if Offside\_Altsel\_Activeiv-149

Purpose: This variable holds the most recent information on the selected state of the vertical ALTSEL mode of the offside FGS.

STATE VARIABLE

## Offside\_ALTSEL\_Active

## Parent:

Offside\_Modesv-135.On  Offside\_ALTSELv-141.Selected  Offside\_ALTSEL\_Selectedv-142.Active

Type: {Capture, Track}ty-23

Initial Value: UNDEFINED

Classified as: MONITORED

:= Capture if not Offside\_Altsel\_Trackiv-150

:= Track if Offside\_Altsel\_Trackiv-150

Purpose: This variable holds the most recent information on the active state of the vertical ALTSEL mode of the offside FGS.

Offside\_VAPPR\_Selected  
Parent: Offside\_Modesv-135.On   
Type: {Cleared, Selected}ty-23   
Initial Value: UNDEFINED   
Classified as: MONITORED   
:= Cleared if not Offside\_Vappr\_Selectediv-150   
:= Selected if Offside\_Vappr\_Selectediv-150

Parent: Offside\_Modesy-135.On  Offside\_VAPPRv-143.Selected   
Type: {Armed, Active}ty-23   
Initial Value: UNDEFINED   
Classified as: MONITORED   
:= Armed if not Offside\_Vappr\_Activeiv-150   
:= Active if Offside\_Vappr\_Activeiv-150   
Purpose: This variable holds the most recent information on the selected state of   
the vertical APPR mode of the offside FGS.

Purpose: This variable holds the most recent information on the base state of the vertical APPR mode of the offside FGS.

STATE VARIABLE

## Offside\_VGA

Parent: Offside\_Modesy-135.On

Type: {Cleared, Selected}ty-23

Initial Value: UNDEFINED

Classified as: MONITORED

:= Cleared if not Offside\_Vga\_Selectediv-151

:= Selected if Offside\_Vga\_Selectediv-151

Purpose: This variable holds the most recent information on the base state of the vertical GA mode of the offside FGS.

Definitions of Values to be Encapsulated

INPUT VARIABLE

Offside\_FGS\_Active

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside FGS believes it is active.

INPUT VARIABLE

## Offside\_FD\_On

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside FD is turned on.

INPUT VARIABLE

## Offside\_Modes\_On

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside modes are on.

INPUT VARIABLE

## Offside\_Roll\_Selected

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside ROLL mode is selected.

# Offside\_Hdg\_Selected

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside Heading mode is selected.

INPUT VARIABLE

## Offside\_Nav\_Selected

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside Nav mode is selected.

INPUT VARIABLE

## Offside\_Nav\_Active

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside Nav mode is active.

# Offside\_Lappr\_Selected

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside Lappr mode is selected.

INPUT VARIABLE

## Offside\_Lappr\_Active

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside Lappr mode is active.

INPUT VARIABLE

## Offside\_Lga\_Selected

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside Lga mode is selected.

# Offside\_Pitch\_Selected

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside vertical Pitch mode is selected.

INPUT VARIABLE

## Offside\_Vs\_Selected

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside vertical Speed mode is selected.

INPUT VARIABLE

## Offside\_Flc\_Selected

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside vertical Flight Level Change mode is selected.

# Offside\_Alt\_Selected

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside vertical Altitude Hold mode is selected.

INPUT VARIABLE

## Offside\_Altsel\_Selected

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside vertical Altitude Select mode is selected.

INPUT VARIABLE

## Offside\_Altsel\_Active

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside vertical Altitude Select mode is active.

# Offside\_Altsel\_Track

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside vertical Altitude Select mode is tracking.

INPUT VARIABLE

## Offside\_Vappr\_Selected

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside Vappr mode is selected.

INPUT VARIABLE

## Offside\_Vappr\_Active

Type: BOOLEAN

Initial Value: UNDEFINED

Classified as: Input

Purpose: This input variable holds the most recent information on whether the offside Vappr mode is active.

# Offside\_Vga\_Selected

Type: BOOLEAN

Initial Value: UNDEFINED

Purpose: This input variable holds the most recent information on whether the offside $\mathrm { V g a }$ mode is selected.

Classified as: Input

## 2.15 FGS Inputs

This section defines the physical interface for all inputs to the FGS. The input variables associated with these fields are defined in the part of the specification to which they are logically related.

<table><tr><td colspan="4">MESSAGE</td><td></td></tr><tr><td></td><td></td><td>Other_Input_Msg</td><td></td><td></td></tr><tr><td></td><td>Fields: AltSel</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, AltselAct</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, AltselSel</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, AltselTrk</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, FdOn</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, FGSActive</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, FlcSel</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, HdgSel</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, LapprAct</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, LapprSel</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, LgaSel</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, ModesOn</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, NavAct</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, NavSel</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, PthSel</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, RollSel</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, VapprAct</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td></td><td>, VapprSel</td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td>, VgaSel</td><td></td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td>, VsSel</td><td></td><td>is</td><td>BOOLEAN</td><td></td></tr><tr><td colspan="3"></td><td>MESSAGE</td><td></td></tr><tr><td colspan="6">This_Input_Msg</td></tr></table>

<table><tr><td>Fields: AltPreRefChanged , AltselCaptureCondMet</td><td></td><td>BOOLEAN</td></tr><tr><td></td><td>is</td><td>BOOLEAN</td></tr><tr><td>, AltselTargetAltChanged</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, AltselTrackCondMet</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, AltSwi</td><td>is</td><td>{OFF, ON}ty-117</td></tr><tr><td>, ApDiscSwi</td><td>is</td><td>{OFF, ON}ty-117</td></tr><tr><td>, ApEngSwi</td><td>is</td><td>{OFF, ON}ty-117</td></tr><tr><td>, ApprSwi</td><td>is</td><td>{OFF, ON}ty-117</td></tr><tr><td>, FdSwi</td><td>is</td><td>{OFF, ON}ty-117</td></tr><tr><td>, FlcSwi</td><td>is</td><td>{OFF, ON}ty-117</td></tr><tr><td>, GaSwi , HdgSwi</td><td>is is</td><td>{OFF, ON}ty-117</td></tr><tr><td></td><td>is</td><td>{OFF, ON}ty-117</td></tr><tr><td>, LapprTrackCondMet , NavSwi</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, NavTrackCondMet</td><td>is</td><td>{OFF, ON}ty-117 BOOLEAN</td></tr><tr><td>, Overspeed</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, SyncSwi</td><td>is</td><td>{OFF, ON}ty-117</td></tr><tr><td>, TransSwi</td><td>is</td><td></td></tr><tr><td>, VapprTrackCondMet</td><td>is</td><td>{OFF, ON}ty-117 BOOLEAN</td></tr><tr><td>, VsPthWhlMot</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, VsSwi</td><td>is</td><td>{OFF, ON}ty-117</td></tr><tr><td></td><td></td><td></td></tr><tr><td></td><td colspan="2">INPUT INTERFACE</td></tr></table>

Other\_Input

Min. Separation: UNDEFINED Max. Separation: UNDEFINED Input Action: READ(Other\_Input\_Msgm-152)

Handler Guard Condition: TRUE

<table><tr><td rowspan=1 colspan=4>Assignment(s) Offside_Alt_Selectediv-149      is assigned</td><td rowspan=1 colspan=1>AltSel</td></tr><tr><td rowspan=1 colspan=4>Offside_Altsel_Activeiv-149     is assigned</td><td rowspan=1 colspan=1>AltselAct</td></tr><tr><td rowspan=1 colspan=4>Offside_Altsel_Selectediv-149  is assigned</td><td rowspan=1 colspan=1>AltselSel</td></tr><tr><td rowspan=1 colspan=5>Offside_Altsel_Trackiv-150      is assigned  AltselTrk</td></tr><tr><td rowspan=1 colspan=5>Offside_FD_Oniv-145             is assigned  FdOn</td></tr><tr><td rowspan=1 colspan=5>Offside_FGS_Activeiv-144      is assigned  FGSActive</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=3>Offside_Flc_Selectediv-148      is assigned</td><td rowspan=1 colspan=1>FlcSel</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Offside_Hdg_Selectediv-146</td><td rowspan=1 colspan=2>is assigned</td><td rowspan=1 colspan=1>HdgSel</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=3>Offside_Lappr_Selectediv-147  is assigned</td><td rowspan=1 colspan=1>LapprSel</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Offside_Lappr_Activeiv-147</td><td rowspan=1 colspan=2>is assigned</td><td rowspan=1 colspan=1>LapprAct</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Offside_Lga_Selectediv-147</td><td rowspan=1 colspan=2>is assigned</td><td rowspan=1 colspan=1>LgaSel</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Offside_Modes_Oniv-145</td><td rowspan=1 colspan=2>is assigned</td><td rowspan=1 colspan=1>ModesOn</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Offside_Nav_Activeiv-146</td><td rowspan=1 colspan=1>is</td><td rowspan=1 colspan=1>assigned</td><td rowspan=1 colspan=1>NavAct</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Offside_Nav_Selectediv-146</td><td rowspan=1 colspan=2>is assigned</td><td rowspan=1 colspan=1>NavSel</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Offside_Pitch_Selectediv-148</td><td rowspan=1 colspan=3>is assigned  PthSel</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Offside_Roll_Selectediv-145</td><td rowspan=1 colspan=3>is assigned  RollSel</td></tr><tr><td rowspan=1 colspan=2>Offside_Vappr_Selectediv-150</td><td rowspan=1 colspan=3>is assigned  VapprSel</td></tr><tr><td rowspan=1 colspan=2>Offside_Vappr_Activeiv-150</td><td rowspan=1 colspan=3>is assigned  VapprAct</td></tr><tr><td rowspan=1 colspan=2>Offside_Vga_Selectediv-151</td><td rowspan=1 colspan=3>is assigned  VgaSel</td></tr><tr><td rowspan=1 colspan=5>Offside_Vs_Selectediv-148       is assigned  VsSel</td></tr></table>

## This\_Input

Min. Separation: UNDEFINED

Max. Separation: UNDEFINED

Input Action: READ(This\_Input\_Msgm-152)

## Handler

Guard Condition: TRUE

Is\_ALTSEL\_Capture\_Cond\_Metiv-101

ALTSEL\_Target\_Altitude\_Changedv-129

Is\_ALTSEL\_Track\_Cond\_Metiv-101

ALT\_Switchv-121

AP\_Disconnect\_Switchiv-126

AP\_Engage\_Switchiv-126

APPR\_Switchv-123

FD\_Switchiv-118

FLC\_Switchv-122

GA\_Switchiv-124

HDG\_Switchiv-118

Is\_LAPPR\_Track\_Cond\_Metiv-101

NAV\_Switchv-119

Is\_NAV\_Track\_Cond\_Metiv-100

Overspeedv-128

SYNC\_Switchv-125

Transfer\_Switchv-125

Is\_VAPPR\_Track\_Cond\_Metiv-102

VS\_Pitch\_Wheel\_In\_Motioniv-125

VS\_Switchv-120

is assigned AltselCaptureCondMet

is assigned AltselTargetAltChanged

is assigned AltselTrackCondMet

is assigned AltSwi

is assigned ApDiscSwi

is assigned ApEngSwi

is assigned ApprSwi

is assigned FdSwi

is assigned FlcSwi

is assigned GaSwi

is assigned HdgSwi

is assigned LapprTrackCondMet

is assigned NavSwi

is assigned NavTrackCondMet

is assigned Overspeediv-128

is assigned SyncSwi

is assigned TransSwi

is assigned VapprTrackCondMet

is assignedVsPthWhlMot

is assigned VsSwi

## 2.16 FGS Outputs

This section defines the physical interface for all outputs from the FGS. The output variables associated with these fields are defined in the part of the specification to which they are logically related.

<table><tr><td colspan="4"></td></tr><tr><td></td><td></td><td>This_Output_Msg</td></tr><tr><td>Fields: AltLamp</td><td></td><td>{OFF, ON}ty-118</td></tr><tr><td>, AltSel</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, AltselAct</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, AltselSel</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, AltselTrk</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, ApEng</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, ApLamp</td><td>is</td><td>{OFF, ON}ty-118</td></tr><tr><td>, ApprLamp</td><td>is</td><td>{OFF, ON}ty-118</td></tr><tr><td>, FdOn</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, FGSActive</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, FlcLamp</td><td>is</td><td>{OFF, ON}ty-118</td></tr><tr><td>, FlcSel</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, HdgLamp</td><td>is</td><td>{OFF, ON}ty-118</td></tr><tr><td>, HdgSel</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, LapprAct</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, LapprSel</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, LgaSel</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, ModesOn</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, NavAct</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, NavLamp</td><td>is</td><td>{OFF, ON}ty-118</td></tr><tr><td>, NavSel</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, PilotFlying</td><td>is</td><td>{LEFT, RIGHT}ty-23</td></tr><tr><td>, PthSel</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, RollSel</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, VapprAct</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, VapprSel</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, VgaSel</td><td>is</td><td>BOOLEAN</td></tr><tr><td>, VsLamp</td><td>is</td><td>{OFF, ON}ty-118</td></tr><tr><td>, VsSel</td><td>is</td><td>BOOLEAN</td></tr></table>

When\_Vertical\_Mode\_Changed  
Condition:
<table><tr><td rowspan=1 colspan=1> $\mathrm { C h a n g e d ( I s \mathrm { \_ R O L L } \mathrm { . S e l e c t e d } _ { v - 3 8 } ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { C h a n g e d ( I s \_ H D G \_ S e l e c t e d _ { v - 4 1 } ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { C h a n g e d ( I s \_ N A V \_ S e l e c t e d _ { v - 4 6 } ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { C h a n g e d ( I s \mathrm { { \_ N A V \mathrm { - } A c t i v e _ { v - 4 6 } } ) } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { C h a n g e d ( I s \mathrm { . } L A P P R \mathrm { . } S e l e c t e d _ { v - 5 2 } ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Changed(Is_LAPPR. $\mathrm { A c t i v e } _ { \mathrm { v } - 5 2 } )$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>·</td></tr><tr><td rowspan=1 colspan=1> $\mathrm { C h a n g e d ( I s \_ L G A \_ S e l e c t e d _ { v - 5 7 } ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td></tr></table>

MACRO

Condition:
<table><tr><td rowspan=11 colspan=1>4 $D</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td rowspan=1 colspan=1>Changed(Is_PITCH_Selectedy-63)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1><eq>\mathrm { C h a n g e d ( I s \mathrm { _ - } V S \mathrm { _ - } S e l e c t e d _ { v - 6 6 } ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { C h a n g e d ( I s \_ A L T \_ S e l e c t e d _ { v - 7 4 } ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { C h a n g e d ( I s \mathrm { _ {- } A L T S E L \mathrm { _ { - } S e l e c t e d _ { v - 7 9 } } ) } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { C h a n g e d ( I s \mathrm { \_ A L T S E L \mathrm { - } A c t i v e _ { v \mathrm { - } 8 0 } ) } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>\big | \mathrm { C h a n g e d ( I s \mathrm { \_ A L T I S E L \mathrm { - } T r a c k _ { v - 8 0 } } ) }</eq></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { C h a n g e d ( I s . F L C . S e l e c t e d _ { v - 7 0 } ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>●</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { C h a n g e d ( I s \mathrm { _ { - } V A P P R \mathrm { \mathrm { . } S e l e c t e d _ { v - 8 7 } } ) } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { C h a n g e d ( I s \mathrm { . } V A P P R \mathrm { . } A c t i v e _ { v - 8 7 } ) }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1> $\mathrm { C h a n g e d ( I s \mathrm { _ - V G A \mathrm { _ - S e l e c t e d _ { v } \mathrm { _ - 9 2 } } ) } }$ </td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>日</td><td rowspan=1 colspan=1>日</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>T</td></tr></table>

OR

OR

# When\_Lamp\_Changed

## Condition:

<table><tr><td rowspan=1 colspan=1>Changed(AP_Lampv-126)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Changed(APPR_Lampv-124)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Changed(HDG_Lampv-119)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Changed(NAV_Lampv-120)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>●</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Changed(VS_Lampv-121)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Changed(ALT_Lampv-122)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Changed(FLC_Lampv-123)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Changed(APPR_Lampv-124)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

This\_Output  
Min. Separation: UNDEFINED  
Max. Separation: UNDEFINED  
Output Action: PUBLISH(This\_Output\_Msgm-156)  
Handler  
Guard Condition:
<table><tr><td rowspan=1 colspan=1>Changed(Mode_Annunciations_Onv-33)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>·</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Changed(Pilot_Flyingv-29)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Changed(Onside_FD_Onv-28)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Changed(Is_This_Side_Activev-30)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Changed(Is_AP_Engagedv-131)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td></tr><tr><td rowspan=1 colspan=1>When_Lateral_Mode_Changedm-157()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>.</td></tr><tr><td rowspan=1 colspan=1>When_Vertical_Mode_Changedm-157()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>T</td><td rowspan=1 colspan=1>.</td></tr><tr><td rowspan=1 colspan=1>When_Lamp_Changedm-158()</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1>.</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>t</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>T</td></tr></table>

<table><tr><td>Assignment(s)</td><td>AltLamp</td><td>is assigned</td><td>ALT_Lampv-122</td></tr><tr><td></td><td>AltSel</td><td>is assigned</td><td>Is_ALT_Selectedy-74</td></tr><tr><td></td><td>AltselAct</td><td>is assigned</td><td>Is_ALTSEL_Activev-80</td></tr><tr><td></td><td>AltselSel</td><td>is assigned</td><td>Is_ALTSEL_Selectedv-79</td></tr><tr><td></td><td>AltselTrk</td><td>is assigned</td><td>Is_ALTSEL_Trackv-80</td></tr><tr><td></td><td>ApEng</td><td>is assigned</td><td>Is_AP_Engagedv-131</td></tr><tr><td></td><td>ApLamp</td><td>is assigned</td><td>AP_Lampv-126</td></tr><tr><td></td><td>ApprLamp</td><td>is assigned</td><td>APPR_Lampv-124</td></tr><tr><td></td><td>FdOn</td><td>is assigned</td><td>Onside_FD_Onv-28</td></tr><tr><td></td><td>FGSActive</td><td>is assigned</td><td>Is_This_Side_Activev-30</td></tr><tr><td></td><td>FlcLamp</td><td>is assigned</td><td>FLC_Lampv-123</td></tr><tr><td></td><td>FlcSel</td><td>is assigned</td><td>Is_FLC_Selectedy-70</td></tr><tr><td></td><td>HdgLamp</td><td>is assigned</td><td>HDG_Lampv-119</td></tr><tr><td></td><td>HdgSel</td><td>is assigned</td><td>Is_HDG_Selectedv-41</td></tr><tr><td></td><td>LapprSel</td><td>is assigned</td><td>Is_LAPPR_Selectedy-52</td></tr><tr><td></td><td>LapprAct</td><td>is assigned</td><td>Is_LAPPR_Activev-52</td></tr><tr><td></td><td>LgaSel</td><td>is assigned</td><td>Is_LGA_Selectedy-57</td></tr><tr><td></td><td>ModesOn</td><td>is assigned</td><td>Mode_Annunciations_Onv-33</td></tr><tr><td></td><td>NavAct</td><td>is assigned</td><td>Is_NAV_Activev-46</td></tr><tr><td></td><td>NavLamp</td><td>is assigned</td><td>NAV_Lampv-120</td></tr><tr><td></td><td>NavSel</td><td>is assigned</td><td>Is_NAV_Selectedy-46</td></tr><tr><td></td><td>PilotFlying</td><td>is assigned</td><td>Pilot_Flyingv-29</td></tr><tr><td></td><td>PthSel</td><td>is assigned</td><td>Is_PITCH_Selectedy-63</td></tr><tr><td></td><td>RollSel</td><td>is assigned</td><td>Is_ROLL_Selectedy-38</td></tr><tr><td></td><td>VapprSel</td><td>is assigned</td><td>Is_VAPPR_Selectedy-87</td></tr><tr><td></td><td>VapprAct</td><td>is assigned</td><td>Is_VAPPR_Activev-87</td></tr><tr><td></td><td>VgaSel</td><td>is assigned</td><td>Is_VGA_Selectedy-92</td></tr><tr><td></td><td>VsLamp</td><td>is assigned</td><td>VS_Lampv-121</td></tr><tr><td></td><td>VsSel</td><td>is assigned</td><td>Is_VS_Selectedy-66</td></tr></table>

Action: SEND

## Bibliography

[1] Anonymous. Mission critical systems: Defense attempting to address major software challenges. Technical Report GAO/IMTEC-93-13, U.S. General Accounting Office, 1992.

[2] Anonymous. Joint advisory circular: Flight guidance system approval. Technical Report AC/ACJ 25.1329, Federal Aviation Administration, 2001.

[3] Barry Boehm. Prentice-Hall, Englewood Cliffs, NJ, 1981.

[4] Fred Brooks. No silver bullet: : Essence and accidents of software engineering. IEEE Computer, pages 10–19, April 1997.

[5] David Harel and Amnon Naamad. The STATEMATE semantics of statecharts. ACM Transactions on Software Engineering and Methodology (TOSEM), 5(4):293–333, October 1996.

[6] Matts Heimdahl and Nancy G. Leveson. Completeness and consistency in hierarchical state-based requirements. IEEE Transactions on Software Engineering, 22(6):363–377, June 1996.

[7] Constance L. Heitmeyer, James Kirby, , and Bruce G. Labaw. Automated consistency checking of requirements specification. ACM Transactions on Software Engineering and Methodology (TOSEM), 5(3):231–261, July1996.

[8] Nancy Leveson, Matts Heimdahl, Holly Hildreth, and Jon Reese. Requirements specifications for process-control systems. IEEE Transactions on Software Engineering, 20(9):684–707, September 1994.

[9] Nancy Leveson, Denise Pinnel, Sean Sandys, Shuichi Koga, and Jon Reese. Analyzing software specifications for mode confusion potential. 1997.

[10] Nancy Leveson, Sean Sandys, Denise Pinnel, Susan Joslyn, Liliana Alfaro, Zelda Zabinsky, and Alan Shaw. Safety analysis of air traffic control upgrades. Technical report, Safeware Engineering, 1997.

[11] Nancy G. Leveson. Addison-Wesley Publishing Company, Reading, Massachusetts, 1995.

[12] Robyn Lutz. Analyzing software requirements errors in safety-critical, embedded systems. In IEEE Symposium on Requirements Engineering, San Diego, CA, 1993.

[13] Steven P. Miller. Specifying the mode logic of a flight guidance system in core and scr. In Second Workshop on Formal Methods in Software Practice (FMSP98), Clearwater Beach, Florida, 1998.

[14] E. H. Phillip. Global teamwork called key to improving aviation safety. Aviation Week & Space Technology, page 70, July 2001.

## Index

ALTSEL (State Variable) Definition, 82 Reference(s), 79, 83, 84

ALT (State Variable) Definition, 76 Reference(s), 74, 75

ALT\_Lamp (State Variable) Definition, 122 Reference(s), 158, 160

ALT\_Switch (Input Variable) Definition, 121 Reference(s), 112, 155

ALTSEL\_Active (State Variable) Definition, 84 Reference(s), 80

ALTSEL\_Selected (State Variable) Definition, 83 Reference(s), 80, 81, 84

ALTSEL\_Target\_Altitude\_Changed (Input Variable) Definition, 129 Reference(s), 113, 155

AP\_Disconnect\_Switch (Input Variable) Definition, 126 Reference(s), 106, 155

AP\_Engage\_Switch (Input Variable) Definition, 126 Reference(s), 105, 155

AP\_Lamp (State Variable) Definition, 126 Reference(s), 158, 160

AP\_State (Type) Definition, 131 Reference(s), 132

APPR\_Lamp (State Variable) Definition, 124 Reference(s), 158, 160

APPR\_Switch (Input Variable) Definition, 123

Reference(s), 114, 155

Activate\_LAPPR (Macro) Definition, 50 Reference(s), 53, 55

Activate\_VAPPR (Macro) Definition, 85 Reference(s), 88, 90

Activate\_NAV (Macro) Definition, 44 Reference(s), 47, 49

Active\_State (Type) Definition, 23 Reference(s), 84, 142

AP (State Variable) Definition, 132 Reference(s), 25, 32, 56, 91, 131

Base\_State (Type) Definition, 23 Reference(s), 39, 43, 48, 54, 59, 64, 68, 72, 76, 82, 89, 94, 136–141, 143, 144

Boolean Reference, 28, 30, 33, 38, 41, 46, 52, 57, 63, 66, 70, 71, 74, 79, 80, 87, 92, 100–102, 125, 127–129, 131, 134, 135, 144–153, 156

Capture\_ALTSEL (Macro) Definition, 78 Reference(s), 81, 83

Deactivate\_ALTSEL (Macro) Definition, 79 Reference(s), 83

Deactivate\_LAPPR (Macro) Definition, 51 Reference(s), 54

Deactivate\_VAPPR (Macro) Definition, 86 Reference(s), 89

Deactivate\_NAV (Macro) Definition, 45 Reference(s), 48

Dearm\_LAPPR(Macro) Definition, 51 Reference(s), 54

Dearm\_NAV (Macro) Definition, 45 Reference(s), 48

Deselect\_ALTSEL (Macro) Definition, 78 Reference(s), 82

Deselect\_LAPPR (Macro) Definition, 51 Reference(s), 54

Deselect\_PITCH (Macro) Definition, 62 Reference(s), 64

Deselect\_ROLL (Macro) Definition, 37 Reference(s), 39

Deselect\_VAPPR (Macro) Definition, 86 Reference(s), 89

Deselect\_ALT (Macro) Definition, 73 Reference(s), 76

Deselect\_FLC (Macro) Definition, 70 Reference(s), 72

Deselect\_HDG (Macro) Definition, 40 Reference(s), 43

Deselect\_LGA (Macro) Definition, 56 Reference(s), 59

Deselect\_NAV (Macro) Definition, 45 Reference(s), 48

Deselect\_VGA (Macro) Definition, 91 Reference(s), 94

Deselect\_VS (Macro) Definition, 65 Reference(s), 68

FD\_Switch (Input Variable) Definition, 118

Reference(s), 103, 155

FLC (State Variable) Definition, 72 Reference(s), 70, 71

FLC\_Lamp (State Variable) Definition, 123 Reference(s), 158, 160

FLC\_Switch (Input Variable) Definition, 122 Reference(s), 111, 155

GA\_Switch (Input Variable) Definition, 124 Reference(s), 115, 155

HDG (State Variable) Definition, 43 Reference(s), 41, 42

HDG\_Lamp (State Variable) Definition, 119 Reference(s), 158, 160

HDG\_Switch (Input Variable) Definition, 118 Reference(s), 108, 155

Independent\_Mode (State Variable) Definition, 31 Reference(s), 30

Independent\_Mode\_Condition (Macro) Definition, 31 Reference(s), 31

Is\_ALT\_Active (State Variable) Definition, 74 Reference(s), 61, 69, 77, 78

Is\_ALT\_Selected (State Variable) Definition, 74 Reference(s), 122, 157, 160

Is\_ALTSEL\_Active (State Variable) Definition, 80 Reference(s), 27, 61, 69, 157, 160

Is\_ALTSEL\_Capture\_Cond\_Met (Input Variable) Definition, 101 Reference(s), 97, 155

Is\_ALTSEL\_Selected (State Variable) Definition, 79 Reference(s), 157, 160

Is\_ALTSEL\_Track (State Variable) Definition, 80 Reference(s), 73, 157, 160

Is\_ALTSEL\_Track\_Cond\_Met (Input Variable) Definition, 101 Reference(s), 96, 155

Is\_AP\_Engaged (State Variable) Definition, 131 Reference(s), 32, 126, 159, 160

Is\_FLC\_Active (State Variable) Definition, 71 Reference(s), 61

Is\_FLC\_Selected (State Variable) Definition, 70 Reference(s), 123, 157, 160

Is\_HDG\_Active (State Variable) Definition, 41 Reference(s), 36

Is\_HDG\_Selected (State Variable) Definition, 41 Reference(s), 119, 157, 160

Is\_LAPPR\_Active (State Variable) Definition, 52 Reference(s), 31, 36, 85, 157, 160

Is\_LAPPR\_Selected (State Variable) Definition, 52 Reference(s), 86, 124, 157, 160

Is\_LAPPR\_Track\_Cond\_Met (Input Variable) Definition, 101 Reference(s), 98, 155

Is\_LGA\_Active (State Variable) Definition, 57 Reference(s), 36

Is\_LGA\_Selected (State Variable) Definition, 57 Reference(s), 157, 160

Is\_NAV\_Active (State Variable) Definition, 46 Reference(s), 36, 157, 160

Is\_NAV\_Selected (State Variable) Definition, 46 Reference(s), 120, 157, 160

Is\_NAV\_Track\_Cond\_Met (Input Variable) Definition, 100 Reference(s), 95, 155

Is\_No\_Nonbasic\_Lateral\_Mode\_Active (Macro) Definition, 36 Reference(s), 37

Is\_No\_Nonbasic\_Vertical\_Mode\_Active (Macro) Definition, 61 Reference(s), 62

Is\_Offside\_LAPPR\_Active (State Variable) Definition, 134 Reference(s), 31

Is\_Offside\_VAPPR\_Active (StateVariable) Definition, 134 Reference(s), 31

Is\_Offside\_VGA\_Active (State Variable) Definition, 135 Reference(s), 31

Is\_PITCH\_Active (State Variable) Definition, 63

Is\_PITCH\_Selected (State Variable) Definition, 63 Reference(s), 157, 160

Is\_ROLL\_Active (State Variable) Definition, 38

Is\_ROLL\_Selected (State Variable) Definition, 38 Reference(s), 157, 160

Is\_This\_Side\_Active (State Variable) Definition, 30 Reference(s), 26, 27, 34, 39, 42, 43, 47–49, 53–55, 58, 59, 64, 67, 68, 71, 72, 75, 76, 81–84, 88–90, 93, 94, 159, 160

Is\_VAPPR\_Active (State Variable) Definition, 87 Reference(s), 27, 31, 61, 65, 69, 73, 77, 78, 157, 160

Is\_VAPPR\_Selected (State Variable) Definition, 87 Reference(s), 124, 157, 160

Is\_VAPPR\_Track\_Cond\_Met (Input Variable) Definition, 102 Reference(s), 99, 155

Is\_VGA\_Active (State Variable) Definition, 92 Reference(s), 31, 61, 77, 78

Is\_VGA\_Selected (State Variable) Definition, 92 Reference(s), 157, 160

Is\_VS\_Active (State Variable) Definition, 66 Reference(s), 27, 61

Is\_VS\_Selected (State Variable) Definition, 66 Reference(s), 121, 157, 160

LAPPR (State Variable)

Definition, 54   
Reference(s), 52, 53, 55

LAPPR\_Selected (State Variable) Definition, 55 Reference(s), 52–54

LGA (State Variable) Definition, 59 Reference(s), 57, 58

Lamp (Type) Definition, 118 Reference(s), 119–124, 126, 156

Mode\_Annunciations\_On (State Variable) Definition, 33 Reference(s), 25–27, 159, 160

Modes (State Variable) Definition, 34 Reference(s), 33, 37, 39, 40, 43, 45, 48, 49, 51, 54–56, 59, 62, 64, 65, 68, 70, 72, 73, 76–78, 82–84, 86, 89–91, 94

NAV (State Variable) Definition, 48 Reference(s), 46, 47, 49

NAV\_Lamp (State Variable) Definition, 120 Reference(s), 158, 160

NAV\_Selected (State Variable) . Definition, 49 Reference(s), 46–48

NAV\_Switch (Input Variable) Definition, 119 Reference(s), 107, 155

No\_Higher\_Event\_Than\_ALT\_Switch\_Pressed (Macro) Definition, 113 Reference(s), 112, 113

No\_Higher\_Event\_Than\_ALTSEL\_Capture\_- Cond\_Met (Macro) Definition, 98 Reference(s), 97

No\_Higher\_Event\_Than\_ALTSEL\_Target\_- Altitude\_Changed (Macro) Definition, 114 Reference(s), 113, 114

No\_Higher\_Event\_Than\_ALTSEL\_Track\_Cond\_- Met (Macro) Definition, 97 Reference(s), 96

No\_Higher\_Event\_Than\_AP\_Disconnect\_Switch\_- Pressed (Macro) Definition, 107 Reference(s), 106, 107

No\_Higher\_Event\_Than\_AP\_Engage\_Switch\_- Pressed (Macro) Definition, 106 Reference(s), 105, 106

No\_Higher\_Event\_Than\_APPR\_Switch\_Pressed (Macro) Definition, 115 Reference(s), 109, 114, 115

No\_Higher\_Event\_Than\_FD\_Switch\_Pressed (Macro) Definition, 104 Reference(s), 96–100, 103

No\_Higher\_Event\_Than\_FLC\_Switch\_Pressed (Macro) Definition, 112 Reference(s), 111, 112

No\_Higher\_Event\_Than\_GA\_Switch\_Pressed (Macro) Definition, 116 Reference(s), 115, 116

No\_Higher\_Event\_Than\_HDG\_Switch\_Pressed (Macro) Definition, 109 Reference(s), 108, 109

No\_Higher\_Event\_Than\_LAPPR\_Track\_Cond\_- Met (Macro) Definition, 99 Reference(s), 98

No\_Higher\_Event\_Than\_NAV\_Switch\_Pressed (Macro) Definition, 108 Reference(s), 105, 108

No\_Higher\_Event\_Than\_NAV\_Track\_Cond\_Met (Macro) Definition, 96 Reference(s), 95

No\_Higher\_Event\_Than\_SYNC\_Switch\_Pressed (Macro) Definition, 117 Reference(s), 116, 117

No\_Higher\_Event\_Than\_Transfer\_Switch\_Pressed (Macro) Definition, 105 Reference(s), 104

No\_Higher\_Event\_Than\_VAPPR\_Track\_Cond\_- Met (Macro) Definition, 100 Reference(s), 99

No\_Higher\_Event\_Than\_VS\_Pitch\_Wheel\_- Rotated (Macro) Definition, 110 Reference(s), 105, 110

No\_Higher\_Event\_Than\_VS\_Switch\_Pressed (Macro) Definition, 111 Reference(s), 110, 111

Offside\_ALTSEL (State Variable) Definition, 141 Reference(s), 82, 142

Offside\_LAPPR (State Variable) Definition, 138 Reference(s), 54, 138

Offside\_PITCH (State Variable) Definition, 139 Reference(s), 64

Offside\_ROLL (State Variable) Definition, 136 Reference(s), 39

Offside\_VAPPR (State Variable) Definition, 143 Reference(s), 89, 143

Offside\_ALT (State Variable) Definition, 141 Reference(s), 76

Offside\_Alt\_Selected (Input Variable) Definition, 149 Reference(s), 141, 154

Offside\_Altsel\_Active (Input Variable) Definition, 149 Reference(s), 142, 154

Offside\_ALTSEL\_Active (State Variable)

Definition, 142   
Reference(s), 84

Offside\_Altsel\_Selected (Input Variable) Definition, 149 Reference(s), 141, 154

Offside\_ALTSEL\_Selected (State Variable) Definition, 142 Reference(s), 83, 142

Offside\_Altsel\_Track (Input Variable) Definition, 150 Reference(s), 142, 154

Offside\_FLC (State Variable) Definition, 140 Reference(s), 72

Offside\_FD (State Variable) Definition, 133 Reference(s), 32

Offside\_FD\_On (Input Variable) Definition, 145 Reference(s), 133, 154

Offside\_FGS\_Active (Input Variable) Definition, 144 Reference(s), 154

Offside\_Flc\_Selected (Input Variable) Definition, 148 Reference(s), 140, 154

Offside\_HDG (State Variable) Definition, 136 Reference(s), 43

Offside\_Hdg\_Selected (Input Variable) Definition, 146 Reference(s), 136, 154

Offside\_LGA (State Variable) Definition, 139 Reference(s), 59

Offside\_Lappr\_Active (Input Variable) Definition, 147 Reference(s), 138, 154

Offside\_Lappr\_Selected (Input Variable) Definition, 147 Reference(s), 138, 154

Offside\_LAPPR\_Selected (State Variable) Definition, 138 Reference(s), 55, 134

Offside\_Lga\_Selected (Input Variable) Definition, 147 Reference(s), 139, 154

Offside\_Modes (State Variable)

Definition, 135   
Reference(s), 30, 34, 136–144

Offside\_Modes\_On (Input Variable) Definition, 145 Reference(s), 135, 154

Offside\_NAV (State Variable) Definition, 137 Reference(s), 48, 137

Offside\_Nav\_Active (Input Variable) Definition, 146 Reference(s), 137, 154

Offside\_Nav\_Selected (Input Variable) Definition, 146 Reference(s), 137, 154

Offside\_NAV\_Selected (State Variable) Definition, 137 Reference(s), 49

Offside\_Pitch\_Selected (Input Variable) Definition, 148 Reference(s), 139, 154

Offside\_Roll\_Selected (Input Variable) Definition, 145 Reference(s), 136, 154

Offside\_VGA (State Variable) Definition, 144 Reference(s), 94, 135

Offside\_Vappr\_Active (Input Variable) Definition, 150 Reference(s), 143, 154

Offside\_Vappr\_Selected (Input Variable) Definition, 150 Reference(s), 143, 154

Offside\_VAPPR\_Selected (State Variable) Definition, 143 Reference(s), 90, 134

Offside\_Vga\_Selected (Input Variable) Definition, 151 Reference(s), 144, 154

Offside\_VS (State Variable) Definition, 140 Reference(s), 68

Offside\_Vs\_Selected (Input Variable) Definition, 148 Reference(s), 140, 154

On\_Off (Type) Definition, 23 Reference(s), 28, 31, 34, 133, 135

Onside\_FD (State Variable)

Definition, 28   
Reference(s), 28, 32

Onside\_FD\_On (State Variable) Definition, 28 Reference(s), 159, 160

Other\_Input (Input Interface) Definition, 153

Other\_Input\_Msg (Message) Definition, 152 Reference(s), 153

Overspeed (Input Variable) Definition, 128 Reference(s), 27, 128, 155

Overspeed\_Condition (Macro) Definition, 128 Reference(s), 25, 26, 56, 65, 69, 70, 85, 91

PITCH (State Variable) Definition, 64 Reference(s), 63

Pilot\_Flying (State Variable) Definition, 29 Reference(s), 25, 29, 30, 159, 160

ROLL (State Variable) Definition, 39 Reference(s), 38

SYNC\_Switch (Input Variable) Definition, 125 Reference(s), 116, 155

Select\_ALTSEL (Macro) Definition, 77 Reference(s), 82

Select\_LAPPR (Macro) Definition, 50 Reference(s), 53, 54

Select\_PITCH (Macro) Definition, 62 Reference(s), 64

Select\_ROLL (Macro) Definition, 37 Reference(s), 39

Select\_VAPPR (Macro) Definition, 85 Reference(s), 89

Select\_ALT (Macro) Definition, 73 Reference(s), 75, 76

Select\_FLC (Macro) Definition, 69 Reference(s), 71, 72

Select\_HDG (Macro) Definition, 40 Reference(s), 42, 43

Select\_LGA (Macro) Definition, 56 Reference(s), 58, 59

Select\_NAV (Macro) Definition, 44 Reference(s), 47, 48

Select\_VGA (Macro) Definition, 91 Reference(s), 93, 94

Select\_VS (Macro) Definition, 65 Reference(s), 67, 68

Selected\_State (Type) Definition, 23 Reference(s), 49, 55, 83, 90, 137, 138, 142, 143

Side (Type) Definition, 23 Reference(s), 29, 156

Switch (Type) Definition, 117 Reference(s), 118–126, 153

THIS\_SIDE (Constant) Definition, 24 Reference(s), 25, 30

This Input (Input Interface) Definition, 155

This\_Input\_Msg (Message) Definition, 152 Reference(s), 155

This\_Output (Output Interface) Definition, 159

This\_Output\_Msg (Message) Definition, 156 Reference(s), 159

Track\_ALTSEL (Macro) Definition, 78 Reference(s), 84

Transfer\_Switch (Input Variable) Definition, 125 Reference(s), 104, 155

VAPPR (State Variable) Definition, 89 Reference(s), 87, 90

VAPPR\_Selected (State Variable) Definition, 90 Reference(s), 87–89

VGA (State Variable) Definition, 94 Reference(s), 92, 93

VS\_Lamp (State Variable) Definition, 121 Reference(s), 158, 160

VS\_Pitch\_Wheel\_In\_Motion (Input Variable) Definition, 125 Reference(s), 109, 155

VS\_Switch (Input Variable) Definition, 120 Reference(s), 110, 155

VS (State Variable) Definition, 68 Reference(s), 66, 67

When\_ALT\_Activated (Macro) Definition, 75 Reference(s), 60, 69

When\_ALT\_Switch\_Pressed (Macro) Definition, 112 Reference(s), 112, 113

When\_ALT\_Switch\_Pressed\_Seen (Macro) Definition, 113 Reference(s), 27, 73

When\_ALTSEL\_Activated (Macro) Definition, 81 Reference(s), 60, 69

When\_ALTSEL\_Capture\_Cond\_Met (Macro) Definition, 97 Reference(s),97

When\_ALTSEL\_Capture\_Cond\_Met\_Seen (Macro) Definition, 97 Reference(s), 78

When\_ALTSEL\_Target\_Altitude\_Changed (Macro) Definition, 113 Reference(s), 113, 114

When\_ALTSEL\_Target\_Altitude\_Changed\_Seen (Macro) Definition, 114

Reference(s), 27, 73, 79

When\_ALTSEL\_Track\_Cond\_Met (Macro) Definition, 96 Reference(s), 96

When\_ALTSEL\_Track\_Cond\_Met\_Seen (Macro) Definition, 96 Reference(s), 78

When\_AP\_Disconnect\_Switch\_Pressed (Macro) Definition, 106 Reference(s), 106, 107

When\_AP\_Disconnect\_Switch\_Pressed\_Seen (Macro) Definition, 107 Reference(s), 130

When\_AP\_Engage\_Switch\_Pressed (Macro) Definition, 105 Reference(s), 105, 106

When\_AP\_Engage\_Switch\_Pressed\_Seen (Macro) Definition, 106 Reference(s), 130

When\_APPR\_Switch\_Pressed (Macro) Definition, 114 Reference(s), 109, 114, 115

When\_APPR\_Switch\_Pressed\_Seen (Macro) Definition, 115 Reference(s), 26, 27, 50, 51, 85, 86

When\_Disengage\_AP (Macro) Definition, 130 Reference(s), 132

When\_Engage\_AP (Macro) Definition, 130 Reference(s), 132

When\_FD\_Switch\_Pressed (Macro) Definition, 103 Reference(s), 96–100, 103

When\_FD\_Switch\_Pressed\_Seen (Macro) Definition, 103 Reference(s), 25, 26

When\_FLC\_Activated (Macro) Definition, 71 Reference(s), 60

When\_FLC\_Switch\_Pressed (Macro) Definition, 111 Reference(s), 111, 112

When\_FLC\_Switch\_Pressed\_Seen (Macro) Definition, 112 Reference(s), 27, 69, 70

When\_GA\_Switch\_Pressed (Macro)

Definition, 115   
Reference(s), 115, 116

When\_GA\_Switch\_Pressed\_Seen (Macro) Definition, 116 Reference(s), 26, 27, 56, 91, 130

When\_HDG\_Activated (Macro) Definition, 42 Reference(s), 35

When\_HDG\_Switch\_Pressed (Macro) Definition, 108 Reference(s), 108, 109

When\_HDG\_Switch\_Pressed\_Seen (Macro) Definition, 109 Reference(s), 26, 40

When\_Lamp\_Changed (Macro) Definition, 158 Reference(s), 159

When\_LAPPR\_Activated (Macro) Definition, 53 Reference(s), 35

When\_LAPPR\_Armed (Macro) Definition, 53 Reference(s), 45

When\_LAPPR\_Track\_Cond\_Met (Macro) Definition, 98 Reference(s), 98

When\_LAPPR\_Track\_Cond\_Met\_Seen (Macro) Definition, 98 Reference(s), 50

When\_Lateral\_Mode\_Changed (Macro) Definition, 157 Reference(s), 159

When\_Lateral\_Mode\_Manually\_Selected (Macro) Definition, 26 Reference(s), 25

When\_LGA\_Activated (Macro) Definition, 58 Reference(s), 35

When\_NAV\_Activated (Macro) Definition, 47 Reference(s), 35

When\_NAV\_Armed (Macro) Definition, 47 Reference(s), 51

When\_NAV\_Switch\_Pressed (Macro) Definition, 107 Reference(s), 105, 108

When\_NAV\_Switch\_Pressed\_Seen (Macro)

Definition, 108   
Reference(s), 26, 44, 45

When\_NAV\_Track\_Cond\_Met (Macro) Definition, 95 Reference(s), 95

When\_NAV\_Track\_Cond\_Met\_Seen (Macro) Definition, 95 Reference(s), 44

When\_Nonbasic\_Lateral\_Mode\_Activated (Macro) Definition, 35 Reference(s), 37, 40, 45, 51, 56, 91

When\_Nonbasic\_Vertical\_Mode\_Activated (Macro) Definition, 60 Reference(s), 56, 62, 65, 70, 73, 79, 86, 91

When\_Pilot\_Flying-Transfer (Macro) Definition, 29 Reference(s), 25, 40, 45, 51, 56, 65, 70, 73, 79, 86, 91

When\_Selected\_Nav\_Frequency\_Changed (State Variable) Definition, 127 Reference(s), 45, 51, 86

When\_Selected\_Nav\_Source\_Changed (State Variable) Definition, 127 Reference(s), 45, 51, 86

When\_SYNC\_Switch\_Pressed (Macro) Definition, 116 Reference(s), 116, 117

When\_SYNC\_Switch\_Pressed\_Seen (Macro) Definition, 117 Reference(s), 56, 91

When\_Transfer\_Switch\_Pressed (Macro) Definition, 104 Reference(s), 104

When\_Transfer\_Switch\_Pressed\_Seen (Macro) Definition, 104 Reference(s), 29

When\_Turn\_FD\_Off (Macro) Definition, 26 Reference(s), 28

When\_Turn\_FD\_On (Macro) Definition, 25 Reference(s), 28

When\_Turn\_Modes\_Off (Macro) Definition, 32

Reference(s), 34

When\_Turn\_Modes\_On (Macro) Definition, 32 Reference(s), 34

When\_VAPPR\_Activated (Macro) Definition, 88 Reference(s), 60

When\_VAPPR\_Track\_Cond\_Met (Macro) Definition, 99 Reference(s), 99

When\_VAPPR\_Track\_Cond\_Met\_Seen (Macro) Definition, 99 Reference(s), 85

When\_Vertical\_Mode\_Changed (Macro) Definition, 157 Reference(s), 159

When\_Vertical\_Mode\_Manually\_Selected (Macro) Definition, 27 Reference(s), 25

When\_VGA\_Activated (Macro) Definition, 93 Reference(s), 60

When\_VS\_Activated (Macro) Definition, 67 Reference(s), 60

When\_VS\_Pitch\_Wheel\_Rotated (Macro) Definition, 109 Reference(s), 105, 110

When\_VS\_Pitch\_Wheel\_Rotated\_Seen (Macro) Definition, 110 Reference(s), 27, 70, 73, 79, 91

When\_VS\_Switch\_Pressed (Macro) Definition, 110 Reference(s), 110, 111

When\_VS\_Switch\_Pressed\_Seen (Macro) Definition, 111 Reference(s), 27, 65

<table><tr><td rowspan=1 colspan=7>Form ApprovedREPORT DOCUMENTATION PAGEOMB No. 0704-0188</td></tr><tr><td rowspan=1 colspan=7>The public reporting burden for this collection of information is estimated to average 1 hour per response, including the time for reviewing instructions, searching existingdata sources,gathering and maintaining the data needed, and completing and reviewing the collection of information. Send comments regarding this burden estimate or any other aspect of thiscollection of information, including suggestions for reducing this burden, to Department of Defense, Washington Headquarters Services, Directorate for Information Operations andReports (0704-0188), 1215 Jefferson Davis Highway, Suite 1204, Arlington, VA 22202-4302. Respondents should be aware that notwithstanding any other provision of law, no personshall be subject to any penalty for failing to comply with a collection of information if it does not display a currently valid OMB control numberPLEASE DO NOT RETURN YOUR FORM TO THE ABOVE ADDRESS.</td></tr><tr><td rowspan=1 colspan=3>1. REPORT DATE (DD-MM-YYYY)01- 06 - 2003</td><td rowspan=1 colspan=4>2. REPORT TYPE                                     3. DATES COVERED (From - To)Contractor Report                                     12/2000-5/2003</td></tr><tr><td rowspan=3 colspan=6>4. TITLE AND SUBTITLEFlight Guidance System Requirements Specification</td><td rowspan=1 colspan=1>5a. CONTRACT NUMBER</td></tr><tr><td rowspan=1 colspan=1>5b. GRANT NUMBER</td></tr><tr><td rowspan=1 colspan=1>5c. PROGRAM ELEMENT NUMBER</td></tr><tr><td rowspan=3 colspan=6>6. AUTHOR(S)Steven P. MillerAlan C. TribbleTimothy M. CarlsonEric J. Danielson</td><td rowspan=1 colspan=1>5d. PROJECT NUMBERNCC1-01001</td></tr><tr><td rowspan=1 colspan=1>5e. TASK NUMBER</td></tr><tr><td rowspan=1 colspan=1>5f. WORK UNIT NUMBER728-30-10-03</td></tr><tr><td rowspan=1 colspan=6>7. PERFORMING ORGANIZATION NAME(S) AND ADDRESS(ES)NASA Langley Research CenterHampton, VA 23681-2199</td><td rowspan=1 colspan=1>8. PERFORMING ORGANIZATIONREPORT NUMBER</td></tr><tr><td rowspan=2 colspan=6>9. SPONSORING/MONITORING AGENCY NAME(S) AND ADDRESS(ES)National Aeronautics and Space AdministrationWashington, DC20546-0001</td><td rowspan=1 colspan=1>10.SPONSOR/MONITOR&#x27;S ACRONYM(S)NASA</td></tr><tr><td rowspan=1 colspan=1>11. SPONSOR/MONITOR&#x27;S REPORTNUMBER(S)NASA/CR-2003-212426</td></tr><tr><td rowspan=1 colspan=7>12. DISTRIBUTION/AVAILABILITY STATEMENTUnclassified - UnlimitedSubject Category 61Availability: NASA CASI (301) 621-0390     Distribution: Standard</td></tr><tr><td rowspan=1 colspan=7>13. SUPPLEMENTARY NOTESAn electronicversion can be found at http://techreports.larc.nasa.gov/ltrs/or http://ntrs.nasa.govLangley Technical Monitor: Ricky W. Butler</td></tr><tr><td rowspan=1 colspan=7>14. ABSTRACTThis report describes a requirements specification written in the RSML-e language for the mode logic of a Flight Guidance System of atypical regional jet aircraft. This model was created as one of the first steps in a five-year project sponsored by the NASA Langley ResearchCenter, Rockwell Collins Inc., and the Critical Systems Research Group of the University of Minnesota to develop new methods and tools toimprove the safety of avionics designs. This model will be used to demonstrate the application of a variety of methods and techniques,including safety analysis of system and subsystem requirements, verification of key properties using theorem provers and model checkers,identification of potential sources mode confusion in system designs, partitioning of applications based on the criticality of system hazards,and autogeneration ofavionics quality code. While this model is representative of the mode logic of a typical regional jet aircraft, it does notdescribe an actual or planned product. Several aspects of a full Flight Guidance System, such as recovery from failed sensors, have beenomitted, and no claims are made regarding the accuracy or completeness of this specification.</td></tr><tr><td rowspan=1 colspan=7>15. SUBJECT TERMSformal methods, requirements, mode confusion, flight guidance system, avionics, formal analysis, flight software</td></tr><tr><td rowspan=1 colspan=4>16. SECURITY CLASSIFICATION OF:</td><td rowspan=3 colspan=1>17. LIMITATION OFABSTRACTUU</td><td rowspan=3 colspan=1>18. NUMBEROFPAGES176</td><td rowspan=2 colspan=1>19a. NAMEOF RESPONSIBLE PERSONSTI Help Desk (email: help@sti.nasa.gov)</td></tr><tr><td rowspan=2 colspan=1>a. REPORTU</td><td rowspan=2 colspan=1>b. ABSTRACTU</td><td rowspan=2 colspan=2>c. THIS PAGEU</td></tr><tr><td rowspan=1 colspan=1>19b. TELEPHONE NUMBER (Include area code)(301) 621-0390</td></tr></table>

Standard Form 298 (Rev. 8-98) Prescribed by ANSI Std. Z39.18