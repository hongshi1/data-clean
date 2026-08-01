# Software Requirements Specification

Sarah Geagea 881024-4940

Sheng Zhang 850820-4735

Niclas Sahlin 880314-5658

Faegheh Hasibi 870625-5166

Farhan Hameed 851007-9695

Elmira Rafiyan 840724-5383

Magnus Ekberg 851022-1933

## Table of Contents

1. Introduction.   
1.1 Purpose.   
1.2 Scope..   
1.3 Definitions, acronyms, and abbreviations.   
1.4 References. 2   
2. Overall description. 4   
2.1 Product perspective.   
2.2 Product functions . 4   
2.3 User characteristics .   
2.4 Constraints ... 5   
2.5 Assumptions and dependencies . 5   
2.6 Apportioning of requirements . 6   
3. Specific requirements. 7   
3.1.1 User interfaces 7   
3.1.2 Hardware interfaces .. 8   
3.1.3 Software interfaces. . 8   
3.1.4 Communications interfaces. .. 9   
3.2 Functional requirements.. . 9   
3.2.1 User Class 1 - The User . .. 9   
3.2.2 User Class 2 - Restaurant Owner .. 14   
3.2.3 User Class 3 - Administrator. .18   
3.3 Performance requirements .. 21   
3.4 Design constraints. .. 23   
3.5 Software system attributes .. 23   
4. Prioritization and Release Plan .. 27   
4.1 Choice of prioritization method .. 27   
Appendix I: Selection for Cost-Value Approach .. 29   
Appendix II: Prioritization Result of 10 selected Requirements Using Cost-Value Approach . .. 32   
Appendix III: Five-Way Priority Scheme... ... 36   
Appendix IV: Release Plan. .. 47   
Appendix V: I-star . .. 55

## 1. Introduction

This section gives a scope description and overview of everything included in this SRS document. Also, the purpose for this document is described and a list of abbreviations and definitions is provided.

## 1.1 Purpose

The purpose of this document is to give a detailed description of the requirements for the “Amazing Lunch Indicator” (ALI) software. It will illustrate the purpose and complete declaration for the development of system. It will also explain system constraints, interface and interactions with other external applications. This document is primarily intended to be proposed to a customer for its approval and a reference for developing the first version of the system for the development team.

## 1.2 Scope

The “Amazing Lunch Indicator” is a GPS-based mobile application which helps people to find the closest restaurants based on the user’s current position and other specification like price, restaurant type, dish and more. The application should be free to download from either a mobile phone application store or similar services.

Restaurant owners can provide their restaurant information using the web-portal. This information will act as the bases for the search results displayed to the user. An administrator also uses the web-portal in order to administer the system and keep the information accurate. The administrator can, for instance, verify restaurant owners and manage user information.

Furthermore, the software needs both Internet and GPS connection to fetch and display results. All system information is maintained in a database, which is located on a web-server. The software also interacts with the GPS-Navigator software which is required to be an already installed application on the user’s mobile phone. By using the GPS-Navigator, users can view desired restaurants on a map and be navigated to them. The application also has the capability of representing both summary and detailed information about the restaurants.

## 1.3 Definitions, acronyms, and abbreviations

Table 1 - Definitions
<table><tr><td colspan="1" rowspan="1">Term</td><td colspan="1" rowspan="1">Definition</td></tr><tr><td colspan="1" rowspan="1">User</td><td colspan="1" rowspan="1">Someone who interacts with the mobile phone application</td></tr><tr><td colspan="1" rowspan="1">Admin/Administrator</td><td colspan="1" rowspan="1">System administrator who is given specific permission for managing andcontrolling the system</td></tr><tr><td colspan="1" rowspan="1">Restaurant Owner</td><td colspan="1" rowspan="1">Someone who has a restaurant and wants his restaurant to be a part theapplication</td></tr><tr><td colspan="1" rowspan="1">Web-Portal</td><td colspan="1" rowspan="1">A web application which present special facilities for restaurant owner</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">and admin</td></tr><tr><td colspan="1" rowspan="1">GPS</td><td colspan="1" rowspan="1">Global Positioning System</td></tr><tr><td colspan="1" rowspan="1">GPS-Navigator</td><td colspan="1" rowspan="1">An installed software on mobile phone which could provide GPSconnection and data, show locations on map and find paths from currentposition to defined destination</td></tr><tr><td colspan="1" rowspan="1">Application Store</td><td colspan="1" rowspan="1">An installed application on mobile phone which helps user to find newcompatible applications with mobile phone platform and download themfrom Internet</td></tr><tr><td colspan="1" rowspan="1">Stakeholder</td><td colspan="1" rowspan="1">Any person who has interaction with the system who is not a developer.</td></tr><tr><td colspan="1" rowspan="1">DESC</td><td colspan="1" rowspan="1">Description</td></tr><tr><td colspan="1" rowspan="1">RAT</td><td colspan="1" rowspan="1">Rational</td></tr><tr><td colspan="1" rowspan="1">DEP</td><td colspan="1" rowspan="1">Dependency</td></tr><tr><td colspan="1" rowspan="1">TAG</td><td colspan="1" rowspan="1">A unique, persistent identifier contained in a PLanguage statement [2]</td></tr><tr><td colspan="1" rowspan="1">GIST</td><td colspan="1" rowspan="1">A short, simple description of the concept contained in a PLanguagestatement [2]</td></tr><tr><td colspan="1" rowspan="1">SCALE</td><td colspan="1" rowspan="1">The scale of measure used by the requirement contained in a PLanguagestatement [2]</td></tr><tr><td colspan="1" rowspan="1">METER</td><td colspan="1" rowspan="1">The process or device used to establish location on a SCALE containedin a PLanguage statement [2]</td></tr><tr><td colspan="1" rowspan="1">MUST</td><td colspan="1" rowspan="1">The minimum level required to avoid failure contained in a PLanguagestatement [2]</td></tr><tr><td colspan="1" rowspan="1">PLAN</td><td colspan="1" rowspan="1">The level at which good success can be claimed contained in a PLanguagestatement [2]</td></tr><tr><td colspan="1" rowspan="1">WISH</td><td colspan="1" rowspan="1">A desirable level of achievement that may not be attainable through availablemeans contained in a PLanguage statement [2]</td></tr><tr><td colspan="1" rowspan="1">DEFINED</td><td colspan="1" rowspan="1">The official definition of a term contained in a PLanguage statement [2]</td></tr></table>

## 1.4 References

[1] IEEE Software Engineering Standards Committee, “IEEE Std 830-1998, IEEE Recommended Practice for Software Requirements Specifications”, October 20, 1998.

[2] Feldt R,”re\_lecture5b\_100914”, unpublished.

[3] Davis M A, “Just Enough Requirements Management: Where Software Development Meets Marketing”, New York, Dorset House Publishing, 2005.

[4] Karlsson J, “A Cost-Value Approach for Prioritizing Requirements”, Norges Teknisk-Naturvitenskapelige Uni. 1997

## 1.5 Overview

The remainder of this document includes three chapters and appendixes. The second one provides an overview of the system functionality and system interaction with other systems. This chapter also introduces different types of stakeholders and their interaction with the system. Further, the chapter also mentions the system constraints and assumptions about the product.

The third chapter provides the requirements specification in detailed terms and a description of the different system interfaces. Different specification techniques are used in order to specify the requirements more precisely for different audiences.

The fourth chapter deals with the prioritization of the requirements. It includes a motivation for the chosen prioritization methods and discusses why other alternatives were not chosen.

The Appendixes in the end of the document include the all results of the requirement prioritization and a release plan based on them.

## 2. Overall description

This section will give an overview of the whole system. The system will be explained in its context to show how the system interacts with other systems and introduce the basic functionality of it. It will also describe what type of stakeholders that will use the system and what functionality is available for each type. At last, the constraints and assumptions for the system will be presented.

## 2.1 Product perspective

This system will consist of two parts: one mobile application and one web portal. The mobile application will be used to find restaurants and view information about them while the web portal will be used for

managing the information about the restaurants and the system as a whole.

The mobile application will need to communicate to a GPS application within the mobile phone, which in turn communicates with a physical GPS device to find the location of the user, see Figure 1. The GPS will provide the mobile application with locations of both the user and the restaurants and the distance between them, but it will also provide maps and the functionality to display the application’s data on the map. The functionality provided by the GPS will be embedded into the application in order for the user to be able to use the functions in the application in a seamlessly manner.

Since this is a data-centric product it will need somewhere to store the data. For that, a database will be used. Both the mobile application and web portal will communicate with the database, however in slightly different ways. The mobile application will only use the database to get data while the web portal will also add and modify data. All of the database communication will go over the Internet.

![](images/8d75730d169a8c73f14775d8025dda0bb1eb96718f77034ab20114fcc903f366.jpg)  
Figure 1 - Block diagram

## The mobile application has some restrictions about the

resource allocation. To avoid problems with overloading the operating system the application is only allowed to use 20 megabytes of memory while running the application. The maximum amount of hard drive space is also 20 megabytes.

## 2.2 Product functions

With the mobile application, the users will be able to search for restaurants. The result will be based on the criteria the user inputs. There are several search criteria and it will be possible for the administrator of the system to manage the options for those criteria that have that.

The result of the search will be viewed either in a list view or in a map view, depending on what criteria included in the search. The list view will have one list item for each restaurant matching the search criteria and show a small part of the restaurant information so the user can identify the restaurant. The

map view will show each restaurant location as a pin on the map as well as the user’s own location. In both views the users will be able to either select a restaurant as target destination or get information how to get there, or view the information of a specific restaurant.

The web portal will provide functionality to manage the system and the restaurant information. It will also provide information about the system, for example show when there is a new update.

## 2.3 User characteristics

There are three types of users that interact with the system: users of the mobile application, restaurant owners and administrators. Each of these three types of users has different use of the system so each of them has their own requirements.

The mobile application users can only use the application to find a restaurant. This means that the user have to be able to search for restaurants, choose a restaurant from that search and then navigate to it. In order for the users to get a relevant search result there are multiple criteria the users can specify and all results matches all of those.

The restaurant owners will not use the mobile application but the web portal instead. There they will manage the information about their restaurant, for example a description of the restaurant, contact information and their menu.

The administrators also only interact with the web portal. They are managing the overall system so there is no incorrect information within it. The administrator can manage the information for each restaurant as well as the options for both the mobile application users and the restaurant owners.

## 2.4 Constraints

The mobile application is constrained by the system interface to the GPS navigation system within the mobile phone. Since there are multiple system and multiple GPS manufacturers, the interface will most likely not be the same for every one of them. Also, there may be a difference between what navigation features each of them provide.

The Internet connection is also a constraint for the application. Since the application fetches data from the database over the Internet, it is crucial that there is an Internet connection for the application to function.

Both the web portal and the mobile application will be constrained by the capacity of the database. Since the database is shared between both application it may be forced to queue incoming requests and therefor increase the time it takes to fetch data.

## 2.5 Assumptions and dependencies

One assumption about the product is that it will always be used on mobile phones that have enough performance. If the phone does not have enough hardware resources available for the application, for example the users might have allocated them with other applications, there may be scenarios where the application does not work as intended or even at all.

Another assumption is that the GPS components in all phones work in the same way. If the phones have different interfaces to the GPS, the application need to be specifically adjusted to each interface and that would mean the integration with the GPS would have different requirements than what is stated in this specification.

## 2.6 Apportioning of requirements

In the case that the project is delayed, there are some requirements that could be transferred to the next version of the application. Those requirements are to be developed in the third release, see Appendix IV.

## 3. Specific requirements

This section contains all of the functional and quality requirements of the system. It gives a detailed description of the system and all its features.

## 3.1 External interface Requirements

This section provides a detailed description of all inputs into and outputs from the system. It also gives a description of the hardware, software and communication interfaces and provides basic prototypes of the user interface.

## 3.1.1 User interfaces

A first-time user of the mobile application should see the log-in page when he/she opens the application, see Figure 2. If the user has not registered, he/she should be able to do that on the log-in page.

If the user is not a first-time user, he/she should be able to see the search page directly when the application is opened, see Figure 3. Here the user chooses the type of search he/she wants to conduct.

Every user should have a profile page where they can edit their e-mail address, phone number and password, see Figure 4. Also, the user can set the mobile application to his/her preferred language. The “P” icon shows where the user can click to navigate to his/her profile page.

![](images/37f3eefd7cc1971aacf5540361a04cabff925c4ef1ab26eaec624b7eab4485b4.jpg)  
Figure 2 - Login page

![](images/9131dff242ce0221b262d05c3ec1133e645af3cb37b89fccfc0df5b09353de66.jpg)  
Figure 3 – Search page

![](images/427499095531bf29f05a1b58d6bac7e4f1b6d5a550e3030ea31beee4ce055911.jpg)  
Figure 4 – Profile page

In Figure 5, the list view for the results is shown. When a user searches by price, this view should be the default one. The sorting header allows the user to sort the results according to price, restaurant name, distance, restaurant type and specific dish. Each result item includes information about the restaurants, a link to the restaurant’s web-page and an information link, which provides a more detailed description of the restaurant. There is also a filtering option, where the user can choose to filter the results by increasing or decreasing the price or distance range, see Figure 7.

In the map view each restaurant is represented by a pin, see Figure 6. Next to every pin there is an information link which provides a more detailed description of the restaurant, as mentioned for the list view. The same filtering option, as for the list view, is included in the map view.

The restaurant owners and administrators interact with the system through a web-portal, see Figure 8. A restaurant owner should be able to register on the web-portal in order to log in and manage the restaurant information. An administrator should also be able to log in to the web-portal where he/she can administer the system by for instance editing restaurant or user information.

![](images/8152d7848e286c6e05fd7ba59346fca77896739608b65ed6ed90eb1b2fe6c0b9.jpg)

![](images/b7548bae172e47aa4b9ed10322ca3b9ec6b6e874e3021345150d556aea3eacc7.jpg)  
Figure 6 – Map view

![](images/63b8529a263a1aa6efe346f19e0608e94a5c8ec0f6a12ad6827035c2d3bc9bd0.jpg)  
Figure 7 – Filter menu

![](images/cf3d4a65a54a2f1746b29edbe7f08d1e0a755f8b846dd3580332656b5631e98c.jpg)  
Figure 8 – Web Portal

## 3.1.2 Hardware interfaces

Since neither the mobile application nor the web portal have any designated hardware, it does not have any direct hardware interfaces. The physical GPS is managed by the GPS application in the mobile phone and the hardware connection to the database server is managed by the underlying operating system on the mobile phone and the web server.

## 3.1.3 Software interfaces

The mobile application communicates with the GPS application in order to get geographical information about where the user is located and the visual representation of it, and with the database in order to get the information about the restaurants, see Figure 1. The communication between the database and the web portal consists of operation concerning both reading and modifying the data, while the communication between the database and the mobile application consists of only reading operations.

## 3.1.4 Communications interfaces

The communication between the different parts of the system is important since they depend on each other. However, in what way the communication is achieved is not important for the system and is therefore handled by the underlying operating systems for both the mobile application and the web portal.

## 3.2 Functional requirements

This section includes the requirements that specify all the fundamental actions of the software system.

## 3.2.1 User Class 1 - The User

## 3.2.1.1 Functional requirement 1.1

## ID: FR1

TITLE: Download mobile application

DESC: A user should be able to download the mobile application through either an application store or similar service on the mobile phone. The application should be free to download.

RAT: In order for a user to download the mobile application.

DEP: None

## 3.2.1.2 Functional requirement 1.2

## ID: FR2

TITLE: Download and notify users of new releases

DESC: When a new/updated version or release of the software is released, the user should check for these manually. The download of the new release should be done through the mobile phone in the same way as downloading the mobile application.

RAT: In order for a user to download a new/updated release.

DEP: FR1

## 3.2.1.3 Functional requirement 1.3

## ID: FR3

TITLE: User registration - Mobile application

DESC: Given that a user has downloaded the mobile application, then the user should be able to register through the mobile application. The user must provide user-name, password and e-mail address. The user can choose to provide a regularly used phone number.

RAT: In order for a user to register on the mobile application.

DEP: FR1

## 3.2.1.4 Functional requirement 1.4

## ID: FR4

TITLE: User log-in - Mobile application

DESC: Given that a user has registered, then the user should be able to log in to the mobile application. The log-in information will be stored on the phone and in the future the user should be logged in automatically.

RAT: In order for a user to register on the mobile application.

DEP: FR1, FR3

## 3.2.1.5 Functional requirement 1.5

ID: FR5

TITLE: Retrieve password

DESC: Given that a user has registered, then the user should be able to retrieve his/her password by email.

RAT: In order for a user to retrieve his/her password.

DEP: FR1

## 3.2.1.6 Functional requirement 1.6

ID: FR6

TITLE: Mobile application - Search

DESC: Given that a user is logged in to the mobile application, then the first page that is shown should be the search page. The user should be able to search for a restaurant, according to several search options. The search options are Price, Destination, Restaurant type and Specific dish. There should also be a freetext search option. A user should be able to select multiple search options in one search.

RAT: In order for a user to search for a restaurant.

DEP: FR4

## 3.2.1.7 Functional requirement 1.7

ID: FR7

TITLE: Mobile application - Search result in a map view

DESC:

 Search results can be viewed on a map. On the map, the relevant and closest restaurants according to the user’s position are shown.

 A specific pin will represent a specific restaurant location. On each pin there should be an information link.

 There should be maximally 100 results displayed. The map view should have a default zoom.

 The map view should include a button that, when selected, should display different filtering options in a filtering menu.

RAT: The way results are displayed in a map.

DEP: FR6

## 3.2.1.8 Functional requirement 1.8

## ID: FR8

TITLE: Mobile application - Search result in a list view

DESC:

Search results can be viewed in a list. Each element in the list represents a specific restaurant. Each element should include the restaurant name, telephone number, type of food, distance according to the user’s position, average price, a short two-line description, a link to the restaurant’s web-page and an information link.

 There should be maximally 100 results displayed. If the result contains more restaurants than what can be displayed on the screen at one time, the user should be able to scroll through them.

 When searching by price the restaurants should be sorted according to the following order:

1. average price

2. distance

3. restaurant type

4. specific dish

 When searching by a search option, other than price, the restaurants should be sorted according to the following order:

1. distance

2. average price

3. restaurant type

4. specific dish

 The list view should include a header with different selectable sorting options.

 The list view should include a button that, when selected, should display different filtering options in a filtering menu.

RAT: The way results should be displayed in a list.

DEP: FR6

## 3.2.1.9 Functional requirement 1.9

## ID: FR9

TITLE: Mobile application - Navigation to restaurant

DESC: A user should be able to select a pin on a map or an element on a list. When a selection is made, the location of the restaurant should be sent to the mobile phone’s GPS-navigation program. The user should then be navigated to the destination. When the destination is reached, a user should be able to go back to the search page on the mobile application.

RAT: To navigate a user to a chosen restaurant.

DEP: FR7, FR8

## 3.2.1.10 Functional requirement 1.10

## ID: FR10

TITLE: Mobile application - Switch result view

DESC: A user should be able to switch between a map view and a list view for all search options.

RAT: In order for a user to switch between result views.

DEP: FR7, FR8

## 3.2.1.11 Functional requirement 1.11

## ID: FR11

TITLE: Mobile application - Selecting the information link

DESC: A user should be able to select the information link, which is included on all result items. The link will direct the user to an information page, which includes a picture of the restaurant, the restaurant name, address, phone number, e-mail address, type of food, average price, restaurant description and a menu with name, description and price of the different dishes.

RAT: In order to show information about the restaurants.

DEP: FR7, FR8

## 3.2.1.12 Functional requirement 1.12

## ID: FR12

TITLE: Mobile application - Search by price

DESC: A user should be able to input a maximum and a minimum price range. The result is displayed in a list view by default.

RAT: In order for a user to search by price.

DEP: FR8

## 3.2.1.13 Functional requirement 1.13

## ID: FR13

TITLE: Mobile application - Search by destination

DESC: A user should be able to input a maximum and a minimum distance, according to his/her position. By default the minimum distance is set to 0 km and the maximum to 10 km. The user should be able to input a higher or lower maximum distance and a higher minimum distance than set by default. The result is displayed in a map view by default.

RAT: In order for a user to search by destination.

DEP: FR7

## 3.2.1.14 Functional requirement 1.14

## ID: FR14

TITLE: Accepted input for price and destination search

DESC: Integers should be accepted as input when a user searches by price or destination. If the system receives an invalid input the user should be informed and prompted to insert an accepted input.

RAT: In order for a user to search with valid input.

DEP: FR12, FR13

## 3.2.1.15 Functional requirement 1.15

## ID: FR15

TITLE: Mobile application - Search by restaurant type

DESC: A user should be able to select a restaurant type in a given list as input. The result is displayed in a map view by default.

RAT: In order for a user to search by restaurant type.

DEP: FR7

## 3.2.1.16 Functional requirement 1.16

## ID: FR16

TITLE: Mobile application - Search by specific dish

DESC: A user should be able to select a specific dish in a given list as input. The result is displayed in a map view by default.

RAT: In order for a user to search by specific dish.

DEP: FR7

## 3.2.1.17 Functional requirement 1.17

## ID: FR17

TITLE: Mobile application - Free-text search

DESC: A user should be able to conduct a search by providing either restaurant name, restaurant description, restaurant address, restaurant type or restaurant menu in the free-text search field. The result is displayed in a map view by default.

RAT: In order for a user to search through the free-text search.

DEP: FR7

## 3.2.1.18 Functional requirement 1.18

## ID: FR18

TITLE: Mobile application - No match found

DESC: If no match is found the user should be informed but kept on the search page in order to get the possibility to conduct a new search right away.

RAT: In order for user to conduct a new search if no match is found.

DEP: FR5

## 3.2.1.19 Functional requirement 1.19

## ID: FR19

TITLE: Mobile application - Sorting results

DESC: When viewing the results in a list, a user should be able to sort the results according to price, distance, restaurant type, specific dish or restaurant name.

 When sorting by restaurant name, specific dish or restaurant type the results should be ordered alphabetically.

 When sorting by price the results should be ordered from cheapest to most expensive.

 When sorting by distance the results should be ordered from closets to furthest distance according to the user’s position.

When the sort button for a specific search option is clicked, then the order should be reversed and ordered in a descending matter. If the sort button is clicked again the order of the results should be reversed.

RAT: In order for a user to sort results in a list.

DEP: FR8

## 3.2.1.20 Functional requirement 1.20

## ID: FR20

TITLE: Mobile application - Filtering results

DESC: When viewing the results in a list or a map, a user should be able to filter the results in a filtering menu. The filtering options include:

 increasing or decreasing the maximum distance

 increasing or decreasing the maximum price

 choosing a restaurant type

 choosing a specific dish

When filtering the results, only the existing results shall be affected and a new search query should not be sent.

RAT: In order for a user to filter results in a list or a map.

DEP: FR7, FR8

## 3.2.1.21 Functional requirement 1.21

## ID: FR21

TITLE: Mobile application - Profile page

DESC: On the mobile application, a user should have a profile page. On the profile page a user can edit his/her information, which includes the password, e-mail address and phone number. A user should also be able to choose what language the mobile application should be set to. The different language choices are Swedish, English, Spanish and French.

RAT: In order for a user to have a profile page on the mobile application.

DEP: FR1

## 3.2.2 User Class 2 - Restaurant Owner

## 3.2.2.1 Functional requirement 2.1

## ID: FR22

Feature: Create an account

In order to create an account

A restaurant owner

Should register on the web-portal

## Scenario: Required information for registration

Given the restaurant owner wants to create an account

And the restaurant owner does not have an account

When the restaurant owner registers on the web-portal by providing user-name   
And password   
And address   
And e-mail address   
And phone number   
Then the restaurant owner should be able to apply for verification   
Scenario: Full information for registration   
Given the restaurant owner wants to create an account   
And the restaurant owner does not have an account   
When the restaurant owner registers on the web-portal by providing user name   
And password   
And address   
And e-mail address   
And phone number   
And mobile number   
Then the restaurant owner should be able to apply for verification

Scenario: Confirmed registration Given the restaurant owner has applied for verification And has not received a confirmation e-mail after registration When the restaurant owner receives a confirmation e-mail Then the restaurant owner should be able to log in

## 3.2.2.2 Functional requirement 2.2

## ID: FR23

Feature: Restaurant owner log-in In order to use the system A restaurant owner Should be logged in to the web-portal

Scenario: Successful log-in   
Given the restaurant owner wants to log in   
When the restaurant owner logs in with his/her account   
Then the restaurant owner should be logged in as a restaurant owner   
Scenario: Retrieve password   
Given the restaurant owner wants to log in   
And has lost the password   
When the restaurant owner enters his/her email address in the “Retrieve password” form   
And submits the form   
Then the restaurant owner should receive an email containing the password

## 3.2.2.3 Functional requirement 2.3

Feature: Manage information In order to manage information A restaurant owner Should be logged in to the web-portal

Scenario: Show fields for managing information   
Given the restaurant owner is logged in   
When the restaurant owner wants to manage information   
Then the restaurant owner should be able to manage information in a form   
Scenario: Filling in mandatory fields   
Given the restaurant owner wants to fill in the mandatory fields of the form   
When the restaurant owner provides average price   
And address   
And e-mail address   
And phone number   
And restaurant name   
Then the restaurant owner has filled the mandatory fields of the form   
Scenario: Filling in optional fields   
Given the restaurant owner of a restaurant wants to fill in optional fields in the form   
When the restaurant owner provides restaurant description   
And menu   
And type of restaurant   
And picture of restaurant   
And mobile phone   
Then the restaurant owner has filled in optional fields in the form   
Scenario: Filling in menu field   
Given the restaurant owner wants to fill in the menu field in the form   
When the restaurant owner provides dish name   
And dish description   
And dish price   
Then the restaurant owner has filled in the menu field in the form

Scenario: Adding information with mandatory fields Given the restaurant owner has filled in the mandatory fields of the form When the restaurant owner submits the form Then the information about the restaurant should be added

Scenario: Adding information with mandatory and optional fields Given the restaurant owner has filled in the mandatory fields of the form

And filled in one or more optional fields of the form When the restaurant owner submits the form Then the information about the restaurant should be added

## Scenario: Deleting information

Given the restaurant owner is logged in And information exists When the restaurant owner deletes information Then the information should be deleted

## Scenario: Editing information

Given the restaurant owner is logged in And information exists When the restaurant owner edits information Then the information should be edited

## 3.2.2.4 Functional requirement 2.4

## ID: FR25

Feature: Restaurant owner - Selecting preferred language on the web-portal   
In order to understand the web-portal   
A restaurant owner   
Should be able to select a preferred language for the web-portal

## Scenario: Select English as preferred language

Given the restaurant owner wants to select a preferred language When the restaurant owner selects English as a new language Then the web-portal will show all text in English

## Scenario: Select Swedish as preferred language

Given the restaurant owner wants to select a preferred language When the restaurant owner selects Swedish as a new language Then the web-portal will show all text in Swedish

## Scenario: Select French as preferred language

Given the restaurant owner wants to select a preferred language When the restaurant owner selects French as a new language Then the web-portal will show all text in French

## Scenario: Select Spanish as preferred language

Given the restaurant owner wants to select a preferred language When the restaurant owner selects Spanish as a new language Then the web-portal will show all text in Spanish

## 3.2.3 User Class 3 - Administrator

## 3.2.3.1 Functional requirement 3.1

## ID: FR26

## Feature: Administrator log in

In order to administer the system

An administrator

Should be logged in to the web-portal

## Scenario: Successful log-in

Given the administrator wants to log in

When the administrator logs in with an administrator account

Then the administrator should be logged in as an administrator

## 3.2.3.2 Functional requirement 3.2

## ID: FR27

## Feature: Verify restaurant owner

In order to allow a restaurant owner to use the system

## An administrator

Should be able to verify the restaurant owner

## Scenario: Verify a restaurant owner

Given the administrator is logged in

When the administrator verifies a restaurant owner

Then the restaurant owner should be able to log in

And the restaurant owner should be notified by a confirmation email

## Scenario: Reject a restaurant owner

Given the administrator is logged in

When the administrator rejects a restaurant owner

Then the restaurant owner should not be able to log in

And the restaurant owner should be notified by a rejection email

## 3.2.3.3 Functional requirement 3.3

## ID: FR28

## Feature: Manage restaurant types

In order to have a list of restaurant types

An administrator

Should be able to manage the restaurant types

## Scenario: Add a new restaurant type

Given the administrator is logged in

When the administrator creates a new restaurant type

Then the new restaurant type should be added to the list of restaurant types

## Scenario: Editing an existing restaurant type

Given the administrator is logged in

When the administrator edits an existing restaurant type

Then the restaurant type should be updated in the list of restaurant types

## Scenario: Delete a restaurant type

Given the administrator is logged in

When the administrator deletes a restaurant type

Then the deleted restaurant type should be removed from the list of restaurant types

## 3.2.3.4 Functional requirement 3.4

## ID: FR29

## Feature: Manage restaurant dishes

In order to have a list of dishes

An administrator

Should be able to manage the dishes

## Scenario: Add a new dish

Given the administrator is logged in

When the administrator creates a new dish

Then the new dish should be added to the list of dishes

## Scenario: Editing an existing dish

Given the administrator is logged in

When the administrator edits an existing dish

Then the dish should be updated in the list of dishes

## Scenario: Delete a dish

Given the administrator is logged in

When the administrator deletes a dish

Then the deleted dish should be removed from the list of dishes

## 3.2.3.5 Functional requirement 3.5

## ID: FR30

## Feature: Manage restaurant information

In order to manage restaurant information

An administrator

Should be logged in to the web-portal

## Scenario: Add restaurant information

Given the administrator is logged in

When the administrator adds restaurant information

Then the information should be added to the restaurant

## Scenario: Delete restaurant information

Given the administrator is logged in

And information about a restaurant exists When the administrator deletes the information Then the information about the restaurant should be deleted

## Scenario: Edit restaurant information

Given the administrator is logged in And information about a restaurant exists When the administrator edits the information Then the information about the restaurant should be edited

## 3.2.3.6 Functional requirement 3.6

## ID: FR31

Feature: Manage users In order to keep track of the users An administrator Should be able to manage the users

## Scenario: Edit an existing user’s information

Given the administrator is logged in When the administrator edits an existing user Then the user information should be updated

## Scenario: Delete/Inactivate an existing user

Given the administrator is logged in When the administrator deletes an existing user Then the user should be deleted

## 3.2.3.7 Functional requirement 3.7

## ID: FR32

## Feature: Manage restaurant owners

In order to keep track of the restaurant owners An administrator Should be able to manage the restaurant owners

## Scenario: Add a new restaurant owner

Given the administrator is logged in When the administrator creates a new restaurant owner Then the new restaurant owner should be added

## Scenario: Edit an existing restaurant owner

Given the administrator is logged in When the administrator edits an existing restaurant owner Then the restaurant owner information should be updated

## Scenario: Delete an existing restaurant owner

Given the administrator is logged in

When the administrator deletes an existing restaurant owner Then the restaurant owner should be deleted And the restaurant information should be deleted

## 3.2.3.8 Functional requirement 3.8

## ID: FR33

Feature: Administrator - Selecting preferred language on the web-portal   
In order to understand the web-portal   
An administrator   
Should be able to select a preferred language for the web-portal

## Scenario: Select English as preferred language

Given the administrator wants to select a preferred language

When the administrator selects English as a new language

Then the web-portal will show all text in English

## Scenario: Select Swedish as preferred language

Given the administrator wants to select a preferred language

When the administrator selects Swedish as a new language

Then the web-portal will show all text in Swedish

## Scenario: Select French as preferred language

Given the administrator wants to select a preferred language

When the administrator selects French as a new language

Then the web-portal will show all text in French

## Scenario: Select Spanish as preferred language

Given the administrator wants to select a preferred language

When the administrator selects Spanish as a new language

Then the web-portal will show all text in Spanish

## 3.3 Performance requirements

The requirements in this section provide a detailed specification of the user interaction with the software and measurements placed on the system performance.

## 3.3.1 Prominent search feature

## ID: QR1

TITLE: Prominent search feature

DESC: The search feature should be prominent and easy to find for the user.

RAT: In order to for a user to find the search feature easily.

DEP: none

## 3.3.2 Usage of the search feature

## ID: QR2

TITLE: Usage of the search feature

DESC: The different search options should be evident, simple and easy to understand.

RAT: In order to for a user to perform a search easily.

DEP: none

## 3.3.3 Usage of the result in the list view

## ID: QR3

TITLE: Usage of the result in the list view

DESC: The results displayed in the list view should be user friendly and easy to understand. Selecting an element in the result list should only take one click.

RAT: In order to for a user to use the list view easily.

DEP: none

## 3.3.4 Usage of the result in the map view

## ID: QR4

TITLE: Usage of the result in the map view

DESC: The results displayed in the map view should be user friendly and easy to understand. Selecting a pin on the map should only take one click.

RAT: In order to for a user to use the map view easily.

DEP: none

## 3.3.5 Usage of the information link

## ID: QR5

TITLE: Usage of the information link

DESC: The information link should be prominent and it should be evident that it is a usable link.   
Selecting the information link should only take one click.

RAT: In order to for a user to use the information link easily.

DEP: none

## 3.3.6 Response time

## ID: QR6

TAG: ResponseTime

GIST: The fastness of the search

SCALE: The response time of a search

METER: Measurements obtained from 1000 searches during testing.

MUST: No more than 2 seconds 100% of the time.

WISH: No more than 1 second 100% of the time.

## 3.3.7 System dependability

## ID: QR8

TAG: SystemDependability

GIST: The fault tolerance of the system.

SCALE: If the system loses the connection to the Internet or to the GPS device or the system gets some strange input, the user should be informed.

METER: Measurements obtained from 1000 hours of usage during testing.

MUST: 100% of the time.

## 3.4 Design constraints

This section includes the design constraints on the software caused by the hardware.

## 3.4.1 Hard drive space

## ID: QR10

TAG: HardDriveSpace

GIST: Hard drive space.

SCALE: The application’s need of hard drive space.

METER: MB.

MUST: No more than 20 MB.

PLAN: No more than 15 MB.

WISH: No more than 10 MB.

MB: DEFINED: Megabyte

## 3.4.2 Application memory usage

## ID: QR11

TAG: ApplicationMemoryUsage

GIST: The amount of Operate System memory occupied by the application.

SCALE: MB.

METER: Observations done from the performance log during testing

MUST: No more than 20 MB.

PLAN: No more than 16 MB

WISH: No more than 10 MB

Operate System: DEFINED: The mobile Operate System which the application is running on.

MB: DEFINED: Megabyte.

## 3.5 Software system attributes

The requirements in this section specify the required reliability, availability, security and maintainability of the software system.

## 3.5.1 Reliability

## ID: QR9

TAG: SystemReliability

GIST: The reliability of the system.

SCALE: The reliability that the system gives the right result on a search.

METER: Measurements obtained from 1000 searches during testing.

MUST: More than 98% of the searches.

PLAN: More than 99% of the searches.

WISH: 100% of the searches.

## 3.5.2 Availability

## ID: QR7

TAG: SystemAvailability

GIST: The availability of the system when it is used.

SCALE: The average system availability (not considering network failing).

METER: Measurements obtained from 1000 hours of usage during testing.

MUST: More than 98% of the time.

PLAN: More than 99% of the time.

WISH: 100% of the time.

## ID: QR22

TITLE: Internet Connection

DESC: The application should be connected to the Internet.

RAT: In order for the application to communicate with the database.

DEP: none

## ID: QR23

TITLE: GPS Connection

DESC: The application should be connected to the GPS device.

RAT: In order for the application to get the users location, the map and to calculate the distance.

DEP: none

## 3.5.3 Security

## ID: QR12

TAG: CommunicationSecurity

GIST: Security of the communication between the system and server.

SCALE: The messages should be encrypted for log-in communications, so others cannot get user-name and password from those messages.

METER: Attempts to get user-name and password through obtained messages on 1000 log-in session during testing.

MUST: 100% of the Communication Messages in the communication of a log-in session should be encrypted.

Communication Messages: Defined: Every exchanged of information between client and server.

## ID: QR13

TAG: RestaurantOwnerLoginAccountSecurity

GIST: Security of accounts.

SCALE: If a restaurant owner tries to log in to the web portal with a non-existing account then the restaurant owner should not be logged in. The restaurant owner should be notified about log-in failure. METER: 1000 attempts to log-in with a non-existing user account during testing.

MUST: 100% of the time.

## ID: QR14

TAG: AdminLoginAccountSecurity

GIST: Security of accounts.

SCALE: If an admin tries to log in to the web portal with a non-existing account then the admin should not be logged in. The admin should be notified about log-in failure.

METER: 1000 attempts to log-in with a non-existing user account during testing.

MUST: 100% of the time.

## ID: QR15

TAG: RestaurantOwnerAccountSecurity

GIST: Security of restaurant owners accounts.

SCALE: A restaurant owner and IP address should not be able to log-in for a certain time period after three times of failed log-in attempts.

METER: 1000 attempts to log-in during the lock period after user account has been locked because of failed log-in attempts of three times.

MUST: The locking period should be half an hour, and during that period the log-in function is disabled.

## ID: QR16

TAG: AdminAccountSecurity

GIST: Security of admin accounts.

SCALE: An admin and IP address should not be able to log-in to the web portal for a certain time period after three times of failed log-in attempts.

METER: 1000 attempts to log-in during the lock period after user account has been locked because of failed log-in attempts of three times.

MUST: The locking period should be half an hour, and during that period the log-in function is disabled.

## ID: QR17

TAG: UserCreateAccountSecurity

GIST: The security of creating account for users of the system.

SCALE: If a user wants to create an account and the desired user name is occupied, the user should be asked to choose a different user name.

METER: Measurements obtained on 1000 hours of usage during testing.

MUST: 100% of the time.

## ID: QR18

TAG: RestaurantOwnerCreateAccountSecurity

GIST: The security of creating account for restaurant owners of the system.

SCALE: If a restaurant owner wants to create an account and the desired user name is occupied, the restaurant owner should be asked to choose a different user name.

METER: Measurements obtained on 1000 hours of usage during testing.

MUST: 100% of the time.

## 3.5.4 Maintainability

## ID: QR19

TITLE: Application extendibility

DESC: The application should be easy to extend. The code should be written in a way that it favors implementation of new functions.

RAT: In order for future functions to be implemented easily to the application.

DEP: none

## ID: QR21

TITLE: Application testability

DESC: Test environments should be built for the application to allow testing of the applications different functions.

RAT: In order to test the application.

DEP: none

## 3.5.5 Portability

## ID: QR20

TITLE: Application portability

DESC: The application should be portable with iOS and Android.

RAT: The adaptable platform for the application to run on.

DEP: none

## 4. Prioritization and Release Plan

In order to get a view of how to divide the requirements into different releases and what requirements should be included in which release, a prioritization of the requirements is needed. This section discusses the choice of prioritization methods and gives a suggestion of how the release plan for these requirements could look like.

## 4.1 Choice of prioritization method

When prioritizing the requirements the ten most important ones were picked out first. This was done with a simple “1 to 10” ranking method, with one being “not important” and ten “very important”. Based on the elicitation meetings, and the perceived ideas of what was important to the different stakeholders, a number was set for each requirement. The numbers were then summed up for each requirement and the ten with the highest score were chosen to be prioritized with the cost value approach. The results, which are red-marked, can be seen in Appendix I and as shown, it turned out to be five functional requirements and five quality requirements. These requirements were then prioritized according to the cost value approach and the results can be viewed under Appendix II.

The remaining requirements were prioritized according to the “Five-Way Priority Scheme” as shown in Appendix III. This method was chosen since it gives the different stakeholders the same importance and has an enough wide range for determining which requirement is more important than the other [3]. However, in this prioritization process, the development team was not included as a stakeholder since the different features were not considered to be as important to them as for the other stakeholders.

Other methods for prioritization, such as the hundred-dollar test and the yes-no vote, were also considered. The hundred-dollar test is quite similar to the five-way priority scheme, since it also gives a wide range for ranking the requirements. However, it is more easily misused since someone could save all their money and put them on a requirement that they think is very important [3]. Others might not agree that this requirement is important but it might still get the most votes since one person cared about it [3].

The yes-no vote method might be fairly simple to carry out, however the range is too narrow. For instance, if two requirements are not very important it would be hard to determine which of those requirements that is more important than the other [3].

In conclusion, weighing the disadvantages and advantages of these methods against each other lead us to choose the five-way priority scheme.

## 4.2 Release Plan

The requirements were divided into three releases based on the prioritization and their dependencies. The three different releases were assembled so that each would work as a fully functional application.

In the first release the requirements that build up the foundation of the application were included, together with the most highly prioritized requirements and their dependencies.

The second release also includes important requirements. However, these requirements are not vital for a functional application. They are more suited to act as additional features that can contribute to making the software product more attractive.

The third release includes the requirements that can be afforded to discard if the project gets delayed or overruns the budget.

For further details about the release plan, see Appendix IV.

## Appendix I: Selection for Cost-Value Approach

Table 2 – Select of ten most important requirements
<table><tr><td colspan="1" rowspan="1">Requirement ID</td><td colspan="1" rowspan="1">Magnus</td><td colspan="1" rowspan="1">Elmira</td><td colspan="1" rowspan="1">Faegheh</td><td colspan="1" rowspan="1">Niclas</td><td colspan="1" rowspan="1">Farhan</td><td colspan="1" rowspan="1">|Sean</td><td colspan="1" rowspan="1">Sarah</td><td colspan="1" rowspan="1">Total</td></tr><tr><td colspan="1" rowspan="1">FR1</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">47</td></tr><tr><td colspan="1" rowspan="1">FR2</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">28</td></tr><tr><td colspan="1" rowspan="1">FR3</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">44</td></tr><tr><td colspan="1" rowspan="1">FR4</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">39</td></tr><tr><td colspan="1" rowspan="1">FR5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">41</td></tr><tr><td colspan="1" rowspan="1">FR6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">66</td></tr><tr><td colspan="1" rowspan="1">FR7</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">64</td></tr><tr><td colspan="1" rowspan="1">FR8</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">64</td></tr><tr><td colspan="1" rowspan="1">FR9</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">51</td></tr><tr><td colspan="1" rowspan="1">FR10</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">39</td></tr><tr><td colspan="1" rowspan="1">FR11</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">31</td></tr><tr><td colspan="1" rowspan="1">FR12</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">40</td></tr><tr><td colspan="1" rowspan="1">FR13</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">47</td></tr><tr><td colspan="1" rowspan="1">FR14</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">34</td></tr><tr><td colspan="1" rowspan="1">FR15</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">41</td></tr><tr><td colspan="1" rowspan="1">FR16</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">39</td></tr><tr><td colspan="1" rowspan="1">FR17</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">28</td></tr><tr><td colspan="1" rowspan="1">FR18</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">36</td></tr><tr><td colspan="1" rowspan="1">FR19</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">35</td></tr><tr><td colspan="1" rowspan="1">FR20</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">40</td></tr><tr><td colspan="1" rowspan="1">FR21</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">34</td></tr><tr><td colspan="1" rowspan="1">FR22</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">47</td></tr><tr><td colspan="1" rowspan="1">FR23</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">43</td></tr><tr><td colspan="1" rowspan="1">FR24</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">58</td></tr><tr><td colspan="1" rowspan="1">FR25</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">28</td></tr><tr><td colspan="1" rowspan="1">FR26</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">45</td></tr><tr><td colspan="1" rowspan="1">FR27</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">17</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">55</td></tr><tr><td colspan="1" rowspan="1">FR28</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">41</td></tr><tr><td colspan="1" rowspan="1">FR29</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">40</td></tr><tr><td colspan="1" rowspan="1">FR30</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">29</td></tr><tr><td colspan="1" rowspan="1">FR31</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">50</td></tr><tr><td colspan="1" rowspan="1">FR32</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">47</td></tr><tr><td colspan="1" rowspan="1">FR33</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">27</td></tr><tr><td colspan="1" rowspan="1">QR1</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">49</td></tr><tr><td colspan="1" rowspan="1">QR2</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">44</td></tr><tr><td colspan="1" rowspan="1">QR3</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">43</td></tr><tr><td colspan="1" rowspan="1">QR4</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">45</td></tr><tr><td colspan="1" rowspan="1">QR5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">35</td></tr><tr><td colspan="1" rowspan="1">QR6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">56</td></tr><tr><td colspan="1" rowspan="1">QR7</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">17</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">57</td></tr><tr><td colspan="1" rowspan="1">QR8</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">49</td></tr><tr><td colspan="1" rowspan="1">QR9</td><td colspan="1" rowspan="1">|6</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">10</td><td colspan="1" rowspan="1">57</td></tr><tr><td colspan="1" rowspan="1">QR10</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">27</td></tr><tr><td colspan="1" rowspan="1">QR11</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">28</td></tr><tr><td colspan="1" rowspan="1">QR12</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">55</td></tr><tr><td colspan="1" rowspan="1">QR13</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">40</td></tr><tr><td colspan="1" rowspan="1">QR14</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">47</td></tr><tr><td colspan="1" rowspan="1">QR15</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">46</td></tr><tr><td colspan="1" rowspan="1">QR16</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">53</td></tr><tr><td colspan="1" rowspan="1">QR17</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">38</td></tr><tr><td colspan="1" rowspan="1">QR18</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">42</td></tr><tr><td colspan="1" rowspan="1">QR19</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">49</td></tr><tr><td colspan="1" rowspan="1">QR20</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">45</td></tr><tr><td colspan="1" rowspan="1">QR21</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">45</td></tr><tr><td colspan="1" rowspan="1">QR22</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">54</td></tr><tr><td colspan="1" rowspan="1">QR23</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">8</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">49</td></tr></table>

## Appendix II: Prioritization Result of 10 selected Requirements Using Cost-Value Approach

Table 3 – 10 most important requirements
<table><tr><td rowspan=1 colspan=1>Requirement ID</td><td rowspan=1 colspan=1>Title</td><td rowspan=1 colspan=1>Requirement Type</td></tr><tr><td rowspan=1 colspan=1>FR6</td><td rowspan=1 colspan=1>Mobile application - Search</td><td rowspan=1 colspan=1>Function</td></tr><tr><td rowspan=1 colspan=1>FR7</td><td rowspan=1 colspan=1>Mobile application - Search result in a map view</td><td rowspan=1 colspan=1>Function</td></tr><tr><td rowspan=1 colspan=1>FR8</td><td rowspan=1 colspan=1>Mobile application - Search result in a list view</td><td rowspan=1 colspan=1>Function</td></tr><tr><td rowspan=1 colspan=1>FR24</td><td rowspan=1 colspan=1>Restaurant owner manages information</td><td rowspan=1 colspan=1>Function</td></tr><tr><td rowspan=1 colspan=1>FR27</td><td rowspan=1 colspan=1>Administrator verifies restaurant owner</td><td rowspan=1 colspan=1>Function</td></tr><tr><td rowspan=1 colspan=1>QR6</td><td rowspan=1 colspan=1>System response time</td><td rowspan=1 colspan=1>Quality</td></tr><tr><td rowspan=1 colspan=1>QR7</td><td rowspan=1 colspan=1>System Availability</td><td rowspan=1 colspan=1>Quality</td></tr><tr><td rowspan=1 colspan=1>QR9</td><td rowspan=1 colspan=1>System Reliability</td><td rowspan=1 colspan=1>Quality</td></tr><tr><td rowspan=1 colspan=1>QR12</td><td rowspan=1 colspan=1>Communication Security</td><td rowspan=1 colspan=1>Quality</td></tr><tr><td rowspan=1 colspan=1>QR22</td><td rowspan=1 colspan=1>Internet Connection</td><td rowspan=1 colspan=1>Quality</td></tr></table>

Table 4 – Value
<table><tr><td colspan="1" rowspan="1">Value</td><td colspan="1" rowspan="1">FR6</td><td colspan="1" rowspan="1">FR7</td><td colspan="1" rowspan="1">FR8</td><td colspan="1" rowspan="1">FR24</td><td colspan="1" rowspan="1">FR27</td><td colspan="1" rowspan="1">QR6</td><td colspan="1" rowspan="1">QR7</td><td colspan="1" rowspan="1">QR9</td><td colspan="1" rowspan="1">QR12</td><td colspan="1" rowspan="1">QR22</td></tr><tr><td colspan="1" rowspan="1">FR6</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">7</td></tr><tr><td colspan="1" rowspan="1">FR7</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">5</td></tr><tr><td colspan="1" rowspan="1">FR8</td><td colspan="1" rowspan="1">1/7</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">1/6</td><td colspan="1" rowspan="1">1/4</td><td colspan="1" rowspan="1">1/4</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">3</td></tr><tr><td colspan="1" rowspan="1">FR24</td><td colspan="1" rowspan="1">1/7</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">1/4</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">4</td></tr><tr><td colspan="1" rowspan="1">FR27</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">1/6</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">1/9</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">1/7</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">QR6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">6</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">9</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">8</td></tr><tr><td colspan="1" rowspan="1">QR7</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">7</td></tr><tr><td colspan="1" rowspan="1">QR9</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">5</td></tr><tr><td colspan="1" rowspan="1">QR12</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">7</td><td colspan="1" rowspan="1">1/2</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">9</td></tr><tr><td colspan="1" rowspan="1">QR22</td><td colspan="1" rowspan="1">1/7</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">1/3</td><td colspan="1" rowspan="1">1/4</td><td colspan="1" rowspan="1">1/2</td><td colspan="1" rowspan="1">1/8</td><td colspan="1" rowspan="1">1/7</td><td colspan="1" rowspan="1">1/5</td><td colspan="1" rowspan="1">1/9</td><td colspan="1" rowspan="1">1</td></tr></table>

Table 5 – Cost
<table><tr><td rowspan=1 colspan=1>COST</td><td rowspan=1 colspan=1>FR6</td><td rowspan=1 colspan=1>FR7</td><td rowspan=1 colspan=1>FR8</td><td rowspan=1 colspan=1>FR24</td><td rowspan=1 colspan=1>FR27</td><td rowspan=1 colspan=1>QR6</td><td rowspan=1 colspan=1>QR7</td><td rowspan=1 colspan=1>QR9</td><td rowspan=1 colspan=1>QR12</td><td rowspan=1 colspan=1>QR22</td></tr><tr><td rowspan=1 colspan=1>FR6</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>1/2</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>1/7</td><td rowspan=1 colspan=1>1/3</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>1/3</td><td rowspan=1 colspan=1>7</td></tr><tr><td rowspan=1 colspan=1>FR7</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>7</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>1/3</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>5</td></tr><tr><td rowspan=1 colspan=1>FR8</td><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>1/9</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>1/6</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>7</td></tr><tr><td rowspan=1 colspan=1>FR24</td><td rowspan=1 colspan=1>1/3</td><td rowspan=1 colspan=1>1/7</td><td rowspan=1 colspan=1>1/3</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>1/3</td><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>7</td></tr><tr><td rowspan=1 colspan=1>FR27</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>1/3</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>1/3</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>1/7</td><td rowspan=1 colspan=1>1/6</td><td rowspan=1 colspan=1>1/7</td><td rowspan=1 colspan=1>1/6</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=1>QR6</td><td rowspan=1 colspan=1>7</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>9</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>7</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>9</td></tr><tr><td rowspan=1 colspan=1>QR7</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>1/2</td><td rowspan=1 colspan=1>6</td><td rowspan=1 colspan=1>1/3</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>7</td></tr><tr><td rowspan=1 colspan=1>QR9</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>6</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>7</td><td rowspan=1 colspan=1>1/2</td><td rowspan=1 colspan=1>1/2</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>5</td></tr><tr><td rowspan=1 colspan=1>QR12</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>1/3</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>1/3</td><td rowspan=1 colspan=1>6</td><td rowspan=1 colspan=1>1/3</td><td rowspan=1 colspan=1>1/3</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>5</td></tr><tr><td rowspan=1 colspan=1>QR22</td><td rowspan=1 colspan=1>1/7</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>7</td><td rowspan=1 colspan=1>7</td><td rowspan=1 colspan=1>1/2</td><td rowspan=1 colspan=1>1/9</td><td rowspan=1 colspan=1>1/7</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>1/5</td><td rowspan=1 colspan=1>1</td></tr></table>

![](images/61f9e54efefe7bf22db6e6b40df9466e796eeddad1aaf783ce00867fa509cbc8.jpg)  
Figure 9 – Result of AHP method

![](images/421616566bbdb2df8b385f2c7a4bbf7ef95d55503f99b39b6164faf212558b11.jpg)  
Figure 10 – The value distribution and estimated cost

<table><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>FR6</td><td rowspan=1 colspan=1>FR7</td><td rowspan=1 colspan=1>FR8</td><td rowspan=1 colspan=1>FR24</td><td rowspan=1 colspan=1>FR27</td><td rowspan=1 colspan=1>QR6</td><td rowspan=1 colspan=1>QR7</td><td rowspan=1 colspan=1>QR9</td><td rowspan=1 colspan=1>QR12</td><td rowspan=1 colspan=1>QR22</td></tr><tr><td rowspan=1 colspan=1>Cost</td><td rowspan=1 colspan=1>5,31%</td><td rowspan=1 colspan=1>9,18%</td><td rowspan=1 colspan=1>7,91%</td><td rowspan=1 colspan=1>7,65%</td><td rowspan=1 colspan=1>1,73%</td><td rowspan=1 colspan=1>22,55%</td><td rowspan=1 colspan=1>13,92%</td><td rowspan=1 colspan=1>15,43%</td><td rowspan=1 colspan=1>12,60%</td><td rowspan=1 colspan=1>3,71%</td></tr><tr><td rowspan=1 colspan=1>Value</td><td rowspan=1 colspan=1>13,60%</td><td rowspan=1 colspan=1>7,12%</td><td rowspan=1 colspan=1>4,80%</td><td rowspan=1 colspan=1>5,93%</td><td rowspan=1 colspan=1>4,45%</td><td rowspan=1 colspan=1>23,41%</td><td rowspan=1 colspan=1>13,78%</td><td rowspan=1 colspan=1>10,31%</td><td rowspan=1 colspan=1>15,06%</td><td rowspan=1 colspan=1>1,53%</td></tr></table>

Table 6 - The value distribution and estimated cost

## Appendix III: Five-Way Priority Scheme

Table 7 – Data of five-way priority scheme prioritization
<table><tr><td rowspan="2">Requirement ID</td><td colspan="5"></td></tr><tr><td colspan="5">Priority by Stakeholder</td></tr><tr><td rowspan="9">FR1</td><td>Magnus</td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td></td><td>1</td><td>-2</td><td>-2</td><td>2</td></tr><tr><td>Elmira</td><td>1</td><td>-1</td><td>-2</td><td>2</td></tr><tr><td>Niclas</td><td>1</td><td>-2</td><td>-2</td><td>1</td></tr><tr><td>Faegheh</td><td>1</td><td>-2</td><td>-2</td><td>1</td></tr><tr><td>Sarah</td><td>1</td><td>-1</td><td>-1</td><td>1</td></tr><tr><td>Average</td><td>1</td><td>-1,6</td><td>-1,8</td><td>1,4 -1</td></tr><tr><td colspan="5">Sum Rank of</td></tr><tr><td>Req.</td><td></td><td></td><td>13</td><td></td></tr><tr><td rowspan="8">FR2</td><td></td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Magnus</td><td>1</td><td>-2</td><td>-2</td><td>1</td></tr><tr><td>Elmira</td><td>1</td><td>-1</td><td>-2</td><td>1</td></tr><tr><td>Niclas</td><td>0</td><td>-2</td><td>-2</td><td>1</td></tr><tr><td>Faegheh</td><td>-1</td><td>-2</td><td>-2</td><td>0</td></tr><tr><td>Sarah</td><td>0</td><td>-2</td><td>-2</td><td>0</td></tr><tr><td>Average</td><td>0,2</td><td>-1,8</td><td>-2</td><td>0,6</td></tr><tr><td>Sum Rank of</td><td></td><td></td><td></td><td>-3</td></tr><tr><td>Req.</td><td colspan="5"></td></tr><tr><td>FR3</td><td>Magnus</td><td>User 1</td><td>Restaurant owner -2</td><td>Administrator -2</td><td>Customer 1</td></tr><tr><td rowspan="10">FR4</td><td>Elmira</td><td></td><td>-2</td><td>-2</td><td>1</td></tr><tr><td>Niclas</td><td>0</td><td></td><td></td><td></td></tr><tr><td>Faegheh</td><td>1</td><td>22</td><td>-2</td><td>0</td></tr><tr><td></td><td>0</td><td></td><td>-2</td><td>1</td></tr><tr><td>Sarah</td><td>1</td><td>-2</td><td>-1</td><td>1</td></tr><tr><td>Average Sum</td><td>0,6</td><td>-2</td><td>-1,8</td><td>0,8</td></tr><tr><td></td><td></td><td></td><td></td><td>-2,4</td></tr><tr><td>Rank of</td><td></td><td></td><td></td><td></td></tr><tr><td>Req.</td><td></td><td>29</td><td></td><td></td></tr><tr><td>User</td><td></td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Magnus</td><td></td><td>0</td><td>-2</td><td>-2</td><td>0</td></tr><tr><td>Elmira Niclas</td><td></td><td>0</td><td>-2</td><td>-2</td><td>0</td></tr><tr><td></td><td></td><td>1</td><td></td><td>-2</td><td>0</td></tr><tr><td>Faegheh Sarah</td><td></td><td>0</td><td>22</td><td>-2</td><td>-1</td></tr><tr><td>Average</td><td>0</td><td></td><td>-2</td><td>-2</td><td>0</td></tr><tr><td></td><td>0,2</td><td></td><td>-2</td><td>-2</td><td>-0,2</td></tr><tr><td></td><td></td><td></td><td></td><td></td><td>-4</td></tr><tr><td>Req.</td><td colspan="5">Rank of</td></tr><tr><td rowspan="3">FR5</td><td></td><td>User</td><td>41 Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Magnus</td><td>1</td><td>-2</td><td>-2</td><td>0</td></tr><tr><td>Elmira Niclas</td><td>1 0</td><td>-2 -2</td><td>-2 -2</td><td>0</td></tr><tr><td rowspan="5"></td><td>Faegheh Sarah</td><td>-1 0</td><td>-2 -2</td><td>-2 -2</td><td>-1 -1</td></tr><tr><td>Average</td><td>0,2</td><td>-2</td><td>-2</td><td>-0,6</td></tr><tr><td>Sum</td><td></td><td></td><td></td><td>-4,4</td></tr><tr><td>Rank of</td><td colspan="3"></td><td></td></tr><tr><td>Req.</td><td colspan="3">42</td><td></td></tr><tr><td rowspan="8">FR9</td><td></td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Magnus</td><td>1</td><td>1</td><td>22222</td><td>1</td></tr><tr><td>Elmira</td><td>1</td><td>0</td><td></td><td>2</td></tr><tr><td>Niclas</td><td>1</td><td>0</td><td></td><td>-1</td></tr><tr><td>Faegheh</td><td>1</td><td>-2</td><td></td><td>1</td></tr><tr><td>Sarah</td><td>1</td><td>0</td><td></td><td>0</td></tr><tr><td>Average Sum</td><td>1</td><td>-0,2</td><td>-2</td><td>0,6</td></tr><tr><td>Rank of</td><td></td><td></td><td></td><td>-0,6</td></tr><tr><td colspan="2">FR10</td><td colspan="3">8</td><td></td></tr><tr><td rowspan="8"></td><td>Req.</td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Magnus</td><td>1</td><td>-2</td><td>22222</td><td>1</td></tr><tr><td>Elmira</td><td>1</td><td>0</td><td></td><td>0</td></tr><tr><td>Niclas</td><td>1</td><td>-2</td><td></td><td>-2</td></tr><tr><td>Faegheh</td><td>1</td><td>-2</td><td></td><td>-1</td></tr><tr><td>Sarah</td><td>0</td><td>-2</td><td></td><td>0</td></tr><tr><td>Average</td><td>0,8</td><td>-1,6</td><td>-2</td><td>-0,4</td></tr><tr><td>Sum Rank of</td><td></td><td></td><td></td><td>-3,2</td></tr><tr><td></td><td>Req.</td><td colspan="3">36</td><td></td></tr><tr><td rowspan="10">FR11</td><td>Magnus</td><td>User 1</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Elmira</td><td>1</td><td>1</td><td>22222</td><td>1</td></tr><tr><td>Niclas</td><td>0</td><td>1</td><td></td><td>1</td></tr><tr><td>Faegheh</td><td></td><td>1</td><td></td><td>-2</td></tr><tr><td></td><td>0</td><td>1</td><td></td><td>1</td></tr><tr><td>Sarah</td><td>0</td><td>1</td><td></td><td>1</td></tr><tr><td>Average</td><td>0,4</td><td>1</td><td>-2</td><td>0,4</td></tr><tr><td>Sum</td><td></td><td></td><td></td><td>-0,2</td></tr><tr><td>Rank of Req.</td><td></td><td></td><td></td><td></td></tr><tr><td></td><td>User Restaurant owner</td><td>5</td><td></td><td></td></tr><tr><td rowspan="7"></td><td></td><td></td><td>-1</td><td>Administrator</td><td>Customer 0</td></tr><tr><td>Magnus Elmira</td><td>11</td><td>0</td><td>22222</td><td>0</td></tr><tr><td>Niclas</td><td>22</td><td>-2</td><td></td><td>-2</td></tr><tr><td>Faegheh</td><td></td><td>-2</td><td></td><td>0</td></tr><tr><td>Sarah</td><td>2</td><td>-1</td><td></td><td>1</td></tr><tr><td>Average Sum</td><td>1,6</td><td>-1,2</td><td>-2</td><td>-0,2</td></tr><tr><td>Rank of</td><td></td><td></td><td></td><td>-1,8</td></tr><tr><td></td><td>Req.</td><td></td><td>18</td><td></td><td></td></tr><tr><td></td><td></td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>FR13</td><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td>Magnus Elmira</td><td>11</td><td>-1 0</td><td>22</td><td>00</td></tr></table>

<table><tr><td rowspan="5"></td><td>Niclas Faegheh</td><td>2 2</td><td>-2 -2</td><td>22</td></tr><tr><td></td><td></td><td></td><td>1</td></tr><tr><td>Sarah</td><td>2 -1</td><td>-2</td><td>1</td></tr><tr><td>Average</td><td>1,6 -1,2</td><td>-2</td><td>0</td></tr><tr><td>Sum Rank of</td><td></td><td></td><td>-1,6</td></tr><tr><td colspan="5">Req.</td></tr><tr><td rowspan="9">FR14</td><td></td><td>User Restaurant owner</td><td>17 Administrator</td><td>Customer</td></tr><tr><td>Magnus</td><td>1 -1</td><td>-2</td><td>1</td></tr><tr><td>Elmira</td><td>0 -2</td><td>-2</td><td>-1</td></tr><tr><td>Niclas</td><td>1 -2</td><td>-2</td><td>1</td></tr><tr><td>Faegheh</td><td>0</td><td>-2 -2</td><td>0</td></tr><tr><td>Sarah</td><td>0</td><td>-2 -2</td><td>0</td></tr><tr><td>Average</td><td>0,4 -1,8</td><td>-2</td><td>0,2</td></tr><tr><td>Sum</td><td></td><td></td><td>-3,2</td></tr><tr><td>Rank of Req.</td><td>37</td><td></td><td></td></tr><tr><td>FR15</td><td></td><td>User Restaurant owner</td><td>Administrator 222</td><td>Customer</td></tr><tr><td rowspan="10"></td><td>Magnus</td><td>1 -1</td><td></td><td>1</td></tr><tr><td>Elmira</td><td>1</td><td>0</td><td>0</td></tr><tr><td>Niclas</td><td>1</td><td>-2</td><td>-2</td></tr><tr><td>Faegheh</td><td>-2 1</td><td>-2</td><td>0</td></tr><tr><td>Sarah</td><td>1 -1</td><td>-2</td><td>1</td></tr><tr><td>Average</td><td>1 -1,2</td><td>-2</td><td>0</td></tr><tr><td>Sum</td><td></td><td></td><td>-2,2</td></tr><tr><td>Rank of</td><td></td><td></td><td></td></tr><tr><td>Req.</td><td></td><td>24</td><td></td></tr><tr><td>Magnus</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td rowspan="8"></td><td>User</td><td>1 -1</td><td>-2</td><td>1</td></tr><tr><td>Elmira</td><td>1 0</td><td>-2</td><td>0</td></tr><tr><td>Niclas</td><td>1</td><td>-2</td><td></td></tr><tr><td>Faegheh</td><td>1</td><td>22</td><td>-2</td></tr><tr><td></td><td></td><td>-2</td><td>-1</td></tr><tr><td>Sarah</td><td>1</td><td>-2</td><td>1</td></tr><tr><td>Average</td><td>1 -1,4</td><td></td><td>-0,2</td></tr><tr><td>Sum Rank of</td><td></td><td></td><td>-2,6</td></tr><tr><td rowspan="7">FR17</td><td>Req.</td><td>31</td><td></td><td></td></tr><tr><td></td><td>User Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Magnus</td><td>1 -1 0</td><td>-2</td><td>1</td></tr><tr><td>Elmira</td><td>1</td><td></td><td>-1</td></tr><tr><td>Niclas</td><td>1</td><td></td><td>-2</td></tr><tr><td>Faegheh</td><td>0</td><td>-2 -2</td><td>-1</td></tr><tr><td>Sarah</td><td>1 -1</td><td>2222</td><td>0</td></tr><tr><td>Average Sum</td><td>0,8</td><td>-1,2</td><td>-2</td><td>-0,6</td></tr><tr><td>Rank of</td><td colspan="3"></td><td>-3</td></tr><tr><td>Req.</td><td colspan="3">35</td><td></td></tr><tr><td>FR18</td><td>Magnus</td><td>User Restaurant owner 2 -2</td><td>Administrator -2</td><td>Customer 1</td></tr></table>

<table><tr><td rowspan="7"></td><td>Elmira</td><td>1</td><td>-1</td><td></td><td>1</td></tr><tr><td>Niclas</td><td>2</td><td>-2</td><td>222</td><td>0</td></tr><tr><td>Faegheh</td><td>1</td><td>-2</td><td></td><td>-1</td></tr><tr><td>Sarah</td><td>1</td><td>-2</td><td>-2</td><td>0</td></tr><tr><td>Average</td><td>1,4</td><td>-1,8</td><td>-2</td><td>0,2</td></tr><tr><td>Sum</td><td></td><td></td><td></td><td>-2,2</td></tr><tr><td>Rank of Req.</td><td colspan="4"></td></tr><tr><td>FR19</td><td></td><td>User</td><td>25 Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td rowspan="12">FR20</td><td>Magnus</td><td>1</td><td>-2</td><td></td><td>1</td></tr><tr><td>Elmira</td><td>1</td><td>-2</td><td>22</td><td>0</td></tr><tr><td>Niclas</td><td>1</td><td>-2</td><td>-2</td><td>-2</td></tr><tr><td></td><td>1</td><td>-2</td><td></td><td></td></tr><tr><td>Faegheh</td><td>1</td><td>-2</td><td>22</td><td>-1</td></tr><tr><td>Sarah Average</td><td>1</td><td>-2</td><td>-2</td><td>0</td></tr><tr><td>Sum</td><td></td><td></td><td></td><td>-0,4 -3,4</td></tr><tr><td>Rank of</td><td colspan="4"></td></tr><tr><td>Req.</td><td colspan="4">38</td></tr><tr><td>Magnus</td><td>User 1</td><td>Restaurant owner -2</td><td>Administrator -2</td><td>Customer</td></tr><tr><td>Elmira</td><td>2</td><td>-1</td><td>-2</td><td>1 1</td></tr><tr><td>Niclas</td><td>1</td><td>-2</td><td>222</td><td>-2</td></tr><tr><td>Faegheh</td><td>1</td><td>-2</td><td></td><td></td></tr><tr><td>Sarah</td><td>1</td><td>-2</td><td></td><td>0 0</td></tr><tr><td>Average</td><td>1,2</td><td></td><td>-2</td><td></td></tr><tr><td>Sum</td><td></td><td>-1,8</td><td></td><td>0 -2,6</td></tr><tr><td>Rank of</td><td colspan="4"></td></tr><tr><td>Req.</td><td colspan="4">32</td></tr><tr><td rowspan="8">FR21</td><td></td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Magnus</td><td>0</td><td>-2</td><td>-2</td><td>00</td></tr><tr><td>Elmira</td><td>1</td><td>-2</td><td></td><td></td></tr><tr><td>Niclas</td><td>0</td><td></td><td></td><td>-1 -1</td></tr><tr><td>Faegheh</td><td>-1</td><td>22</td><td>222</td><td></td></tr><tr><td>Sarah</td><td>0</td><td>-2</td><td>-2</td><td>0</td></tr><tr><td>Average</td><td>0</td><td>-2</td><td>-2</td><td>-0,4</td></tr><tr><td>Sum Rank of</td><td></td><td></td><td></td><td>-4,4</td></tr><tr><td>Req.</td><td colspan="5"></td></tr><tr><td rowspan="10">FR22</td><td></td><td>User</td><td>43 Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Magnus</td><td>-2</td><td></td><td>-2</td><td></td></tr><tr><td>Elmira</td><td>-2</td><td></td><td></td><td>221</td></tr><tr><td>Niclas</td><td>-2</td><td></td><td></td><td></td></tr><tr><td>Faegheh</td><td>-2</td><td>２２２２２</td><td>222</td><td>2</td></tr><tr><td>Sarah</td><td>-2</td><td></td><td>-2</td><td>1</td></tr><tr><td>Average</td><td>-2</td><td>2</td><td>-2</td><td>1,6</td></tr><tr><td>Sum</td><td></td><td></td><td></td><td>-0,4</td></tr><tr><td>Rank of</td><td></td><td></td><td></td><td></td></tr><tr><td>Req.</td><td colspan="4">6</td></tr><tr><td></td><td></td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td rowspan="7">FR23</td><td>Magnus</td><td>-2</td><td>1</td><td></td><td>2</td></tr><tr><td>Elmira</td><td>-2</td><td>2</td><td>22222</td><td>1</td></tr><tr><td>Niclas</td><td>22</td><td></td><td></td><td>1</td></tr><tr><td>Faegheh</td><td></td><td>22</td><td></td><td>1</td></tr><tr><td>Sarah</td><td>-2</td><td>2</td><td></td><td>1</td></tr><tr><td>Average</td><td>-2</td><td>1,8</td><td>-2</td><td>1,2</td></tr><tr><td>Sum Rank of</td><td></td><td></td><td></td><td>-1</td></tr><tr><td>Req.</td><td colspan="4"></td></tr><tr><td rowspan="8">FR25</td><td>User</td><td>Restaurant owner</td><td>14</td><td>Administrator</td><td>Customer</td></tr><tr><td>Magnus</td><td>-2</td><td>1</td><td>-2</td><td>1</td></tr><tr><td>Elmira</td><td></td><td>1</td><td>-2</td><td>0</td></tr><tr><td>Niclas</td><td>22</td><td>1</td><td></td><td>-2</td></tr><tr><td>Faegheh</td><td>-2</td><td>0</td><td>22</td><td></td></tr><tr><td>Sarah</td><td>-1</td><td>1</td><td>-2</td><td>-1 0</td></tr><tr><td>Average</td><td>-1,8</td><td>0,8</td><td>-2</td><td>-0,4</td></tr><tr><td>Sum</td><td></td><td></td><td></td><td>-3,4</td></tr><tr><td colspan="5">Rank of Req.</td><td></td></tr><tr><td rowspan="9">FR26</td><td></td><td>User</td><td>39 Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Magnus</td><td>-2</td><td>-2</td><td></td><td></td></tr><tr><td>Elmira</td><td></td><td>-2</td><td>2 1</td><td>10</td></tr><tr><td>Niclas</td><td>222</td><td>-2</td><td></td><td>1</td></tr><tr><td>Faegheh</td><td></td><td>-2</td><td>22</td><td>1</td></tr><tr><td>Sarah</td><td>-2</td><td>-2</td><td>2</td><td>1</td></tr><tr><td>Average</td><td>-2</td><td>-2</td><td>1,8</td><td>0,8</td></tr><tr><td>Sum</td><td></td><td></td><td></td><td>-1,4</td></tr><tr><td colspan="5">Rank of Req.</td></tr><tr><td rowspan="10">FR28</td><td>Magnus</td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td></td><td>-2</td><td>0</td><td>1</td><td>1</td></tr><tr><td>Elmira</td><td>-2</td><td>1</td><td>0</td><td>1</td></tr><tr><td>Niclas</td><td>-1</td><td>1</td><td>2</td><td>0</td></tr><tr><td>Faegheh</td><td>-2</td><td>-1</td><td>2</td><td>1</td></tr><tr><td>Sarah</td><td>-1</td><td>0</td><td>1</td><td>1</td></tr><tr><td>Average</td><td></td><td></td><td></td><td></td></tr><tr><td>Sum</td><td>-1,6</td><td>0,2</td><td>1,2</td><td>0,8</td></tr><tr><td>Rank of</td><td></td><td></td><td></td><td>0,6</td></tr><tr><td colspan="5">Req. 2</td></tr><tr><td rowspan="10">FR29</td><td></td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Magnus</td><td>-2</td><td>0</td><td>1</td><td>1</td></tr><tr><td>Elmira</td><td>-2</td><td>1</td><td>0</td><td>1</td></tr><tr><td>Niclas</td><td>-1</td><td>1</td><td>2</td><td>0</td></tr><tr><td>Faegheh</td><td>-2</td><td>-1</td><td>2</td><td>1</td></tr><tr><td>Sarah</td><td>-1</td><td>0</td><td>1</td><td>1</td></tr><tr><td>Average</td><td>-1,6</td><td>0,2</td><td>1,2</td><td>0,8</td></tr><tr><td>Sum</td><td></td><td></td><td></td><td>0,6</td></tr><tr><td>Rank of</td><td></td><td></td><td></td><td></td></tr><tr><td colspan="5">Req. 3</td></tr></table>

<table><tr><td rowspan="5">FR30</td><td rowspan="3">Magnus</td><td>User -2</td><td>Restaurant owner</td><td>Administrator</td><td colspan="2">Customer</td></tr><tr><td></td><td></td><td>0 1 1</td><td colspan="2">1</td></tr><tr><td>Elmira</td><td>-1</td><td>0</td><td colspan="2">1</td></tr><tr><td>Niclas</td><td>-2</td><td>0</td><td>2</td><td colspan="2">0</td></tr><tr><td>Faegheh Sarah</td><td>-2</td><td>1</td><td>2</td><td colspan="2">1</td></tr><tr><td></td><td>-1</td><td>1</td><td>2</td><td colspan="3">1</td></tr><tr><td>Average Sum</td><td>-1,6</td><td>0,4</td><td>1,6</td><td colspan="3">0,8</td></tr><tr><td>Rank of Req.</td><td colspan="3"></td><td colspan="3">1,2</td></tr><tr><td>FR31</td><td></td><td></td><td>1</td><td colspan="3"></td></tr><tr><td rowspan="10"></td><td></td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td colspan="2">Customer</td></tr><tr><td>Magnus</td><td>0</td><td>-2</td><td>1</td><td colspan="2">1</td></tr><tr><td>Elmira</td><td>0</td><td>222</td><td>0</td><td colspan="2">1</td></tr><tr><td>Niclas</td><td>0</td><td></td><td></td><td colspan="2">0</td></tr><tr><td>Faegheh</td><td>0</td><td></td><td>21</td><td colspan="2">0</td></tr><tr><td>Sarah</td><td>0</td><td>-2</td><td>1</td><td colspan="2">1</td></tr><tr><td>Average</td><td>0</td><td>-2</td><td>1</td><td colspan="2"></td></tr><tr><td>Sum</td><td></td><td></td><td></td><td colspan="2">0,6</td></tr><tr><td>Rank of</td><td></td><td></td><td></td><td colspan="2">-0,4</td></tr><tr><td>Req.</td><td></td><td>7</td><td></td><td colspan="2"></td></tr><tr><td>FR32</td><td></td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td colspan="2">Customer</td></tr><tr><td rowspan="8"></td><td>Magnus</td><td>-2</td><td>0</td><td>1</td><td colspan="2">1</td></tr><tr><td>Elmira</td><td>-2</td><td>0</td><td>0</td><td colspan="2">1</td></tr><tr><td>Niclas</td><td>-2</td><td>0</td><td>2</td><td colspan="2">0</td></tr><tr><td>Faegheh</td><td>-2</td><td>1</td><td>1</td><td colspan="2">1</td></tr><tr><td>Sarah</td><td>-2</td><td>0</td><td>1</td><td colspan="2">1</td></tr><tr><td>Average</td><td>-2</td><td>0,2</td><td>1</td><td colspan="2">0,8</td></tr><tr><td>Sum Rank of</td><td></td><td></td><td></td><td colspan="2">0</td></tr><tr><td>Req.</td><td></td><td>4</td><td></td><td colspan="2"></td></tr><tr><td>FR33</td><td></td><td>User</td><td></td><td></td><td colspan="2"></td></tr><tr><td rowspan="10"></td><td>Magnus</td><td>-2</td><td>Restaurant owner</td><td>Administrator</td><td colspan="2">Customer</td></tr><tr><td>Elmira</td><td>-2</td><td>-2</td><td>0</td><td colspan="2">0</td></tr><tr><td>Niclas</td><td></td><td>-2</td><td>0</td><td colspan="2">0</td></tr><tr><td>Faegheh</td><td>-2</td><td>22</td><td>0</td><td colspan="2">-2</td></tr><tr><td></td><td>-2</td><td></td><td>0</td><td colspan="2">-1</td></tr><tr><td>Sarah</td><td>-2</td><td>-2</td><td>0</td><td colspan="2">0</td></tr><tr><td>Average</td><td>-2</td><td>-2</td><td>0</td><td colspan="2">-0,6</td></tr><tr><td>Sum</td><td></td><td></td><td></td><td colspan="2">-4,6</td></tr><tr><td>Rank of Req.</td><td></td><td></td><td></td><td colspan="2"></td></tr><tr><td></td><td></td><td>44</td><td></td><td colspan="2"></td></tr><tr><td rowspan="7">QR1</td><td>Magnus</td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td colspan="2">Customer</td></tr><tr><td>Elmira</td><td>２２２２</td><td>-2</td><td>-2</td><td colspan="2">2２0</td></tr><tr><td>Niclas</td><td></td><td>222</td><td></td><td colspan="2"></td></tr><tr><td>Faegheh</td><td></td><td></td><td>222</td><td colspan="2"></td></tr><tr><td></td><td></td><td></td><td></td><td colspan="2">1</td></tr><tr><td>Sarah</td><td>2</td><td>-2</td><td>-2</td><td colspan="2">1</td></tr><tr><td>Average</td><td>2</td><td>-2</td><td>-2</td><td colspan="2">1,2</td></tr><tr><td>Sum</td><td></td><td></td><td></td><td></td><td colspan="2"></td></tr><tr><td></td><td></td><td></td><td></td><td></td><td colspan="2">-0,8</td></tr><tr><td>Rank of</td><td></td><td></td><td>10</td><td></td><td colspan="2"></td></tr><tr><td></td><td>Req.</td><td colspan="4"></td></tr><tr><td colspan="2">QR2</td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td rowspan="8"></td><td rowspan="2">Magnus Elmira Niclas</td><td>２２２２</td><td>-2 -2</td><td>-2</td><td></td></tr><tr><td></td><td></td><td></td><td>220</td></tr><tr><td>Faegheh</td><td></td><td>22</td><td>2222</td><td></td></tr><tr><td></td><td></td><td></td><td></td><td>1</td></tr><tr><td>Sarah</td><td>2</td><td>-2</td><td></td><td>1</td></tr><tr><td>Average</td><td>2</td><td>-2</td><td>-2</td><td>1,2</td></tr><tr><td>Sum</td><td></td><td></td><td></td><td>-0,8</td></tr><tr><td>Rank of Req.</td><td colspan="4">11</td></tr><tr><td rowspan="7">QR3</td><td rowspan="2">Magnus</td><td colspan="5">User Restaurant owner 1</td></tr><tr><td></td><td>-2</td><td>Administrator 2222</td><td>Customer 1</td></tr><tr><td rowspan="5">Elmira Niclas Faegheh</td><td>1</td><td>-1</td><td></td><td>1</td></tr><tr><td></td><td>-1</td><td></td><td>0</td></tr><tr><td></td><td>-1</td><td></td><td>-1</td></tr><tr><td>Sarah</td><td>0 1 -1</td><td>-2</td><td>1</td></tr><tr><td>Average</td><td>-1,2</td><td>-2</td><td>0,4</td></tr><tr><td>Sum</td><td colspan="5">0,8</td></tr><tr><td>Rank of Req.</td><td colspan="5"></td></tr><tr><td rowspan="5"></td><td></td><td>User</td><td>21 Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Magnus Elmira</td><td>1 1</td><td>-2</td><td>-2</td><td>1</td></tr><tr><td>Niclas</td><td>1</td><td>-1</td><td>222</td><td>1</td></tr><tr><td>Faegheh</td><td>1</td><td>-1</td><td></td><td>0</td></tr><tr><td></td><td>1</td><td>-1</td><td></td><td>0</td></tr><tr><td rowspan="5"></td><td>Sarah Average</td><td></td><td>-1</td><td>-2</td><td>0</td></tr><tr><td>Sum</td><td>1</td><td>-1,2</td><td>-2</td><td>0,4 -1,8</td></tr><tr><td>Rank of</td><td colspan="5"></td></tr><tr><td>Req.</td><td colspan="5">19</td></tr><tr><td></td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td rowspan="7">QR5</td><td>Magnus Elmira</td><td>1</td><td>-1</td><td>-2</td><td>1</td></tr><tr><td>Niclas</td><td>1</td><td>-1</td><td>2222</td><td>1</td></tr><tr><td>Faegheh</td><td>1</td><td>0</td><td></td><td>-2</td></tr><tr><td></td><td>1</td><td>1</td><td></td><td>-1</td></tr><tr><td>Sarah</td><td>0</td><td>-1</td><td></td><td>0</td></tr><tr><td>Average Sum</td><td>0,8</td><td>-0,4</td><td>-2</td><td>-0,2</td></tr><tr><td>Rank of</td><td></td><td></td><td></td><td>-1,8</td></tr><tr><td></td><td colspan="6">Req.</td></tr><tr><td rowspan="6">QR8</td><td>Magnus</td><td>User 1</td><td>Restaurant owner -2</td><td>Administrator</td><td>Customer</td></tr><tr><td>Elmira</td><td>1</td><td></td><td>-2</td><td>10</td></tr><tr><td>Niclas</td><td>1</td><td></td><td></td><td>2</td></tr><tr><td>Faegheh</td><td>1</td><td>222</td><td>222</td><td>0</td></tr><tr><td>Sarah</td><td>0</td><td>-1</td><td>-1</td><td></td></tr><tr><td>Average</td><td>0,8</td><td></td><td></td><td>0</td></tr><tr><td></td><td></td><td></td><td>-1,8</td><td>-1,8</td><td>0,6</td></tr><tr><td>Sum</td><td></td><td></td><td></td><td></td><td>-2,2</td></tr></table>

<table><tr><td rowspan="2"></td><td>Rank of</td><td colspan="3"></td></tr><tr><td>Req.</td><td>26</td><td></td><td></td></tr><tr><td rowspan="9">QR10</td><td></td><td>User Restaurant owner -2</td><td>Administrator</td><td>Customer -1</td></tr><tr><td>Magnus Elmira</td><td>-1 -1 -2</td><td></td><td>0</td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td>Niclas</td><td>-1 -2</td><td>2222</td><td>-1</td></tr><tr><td>Faegheh</td><td>-1 -2</td><td></td><td>-1</td></tr><tr><td>Sarah</td><td>-1 -2</td><td>-2</td><td>0</td></tr><tr><td>Average Sum</td><td>-1 -2</td><td>-2</td><td>-0,6</td></tr><tr><td>Rank of</td><td></td><td></td><td>-5,6</td></tr><tr><td></td><td></td><td>45</td><td></td></tr><tr><td rowspan="9">QR11</td><td>Req.</td><td>User Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Magnus</td><td>-1 -2</td><td>-2</td><td>-1</td></tr><tr><td>Elmira</td><td>0</td><td>-22</td><td></td></tr><tr><td>Niclas</td><td>-1</td><td>-2</td><td>0</td></tr><tr><td>Faegheh</td><td>22 -1</td><td></td><td>-1</td></tr><tr><td>Sarah</td><td>-1</td><td>22</td><td>-1 -1</td></tr><tr><td>Average</td><td>-0,8 -2</td><td>-2</td><td>-0,8</td></tr><tr><td>Sum</td><td></td><td></td><td>-5,6</td></tr><tr><td>Rank of Req.</td><td></td><td></td><td></td></tr><tr><td>QR13</td><td></td><td>User Restaurant owner</td><td>46 Administrator</td><td>Customer</td></tr><tr><td rowspan="10"></td><td>Magnus</td><td>-2</td><td>2 1</td><td></td></tr><tr><td>Elmira</td><td>-2</td><td>-1 -2</td><td>21</td></tr><tr><td>Niclas</td><td>-2</td><td></td><td></td></tr><tr><td>Faegheh</td><td>-2</td><td>22</td><td>21</td></tr><tr><td>Sarah</td><td>-2</td><td>-2</td><td></td></tr><tr><td>Average</td><td>-2</td><td></td><td></td></tr><tr><td>Sum</td><td>1,6</td><td>-1,8</td><td>1,5</td></tr><tr><td>Rank of</td><td></td><td></td><td>-0,7</td></tr><tr><td>Req.</td><td></td><td></td><td></td></tr><tr><td></td><td>User Restaurant owner</td><td>9 Administrator</td><td></td></tr><tr><td rowspan="10">QR14</td><td>Magnus</td><td>-2</td><td></td><td>Customer</td></tr><tr><td>Elmira</td><td></td><td>2</td><td></td></tr><tr><td>Niclas</td><td></td><td>1</td><td></td></tr><tr><td>Faegheh</td><td>2222 222</td><td>22</td><td>2122</td></tr><tr><td>Sarah</td><td></td><td></td><td></td></tr><tr><td></td><td>-2 -2 -2</td><td>1</td><td>1</td></tr><tr><td>Average</td><td>-2</td><td>1,6</td><td>1,6</td></tr><tr><td>Sum</td><td></td><td></td><td>-0,8</td></tr><tr><td>Rank of Req.</td><td></td><td></td><td></td></tr><tr><td></td><td>12 Restaurant owner</td><td>Administrator</td><td></td></tr><tr><td rowspan="10">QR15</td><td></td><td>User 0</td><td></td><td>Customer</td></tr><tr><td>Magnus Elmira</td><td></td><td>2222</td><td>-1</td></tr><tr><td>Niclas</td><td>222</td><td>0 1</td><td></td></tr><tr><td></td><td></td><td></td><td>2221</td></tr><tr><td>Faegheh</td><td>-2</td><td>0 -2</td><td></td></tr><tr><td>Sarah</td><td>-2</td><td>1</td><td></td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td>Average</td><td>-2</td><td></td><td></td></tr><tr><td></td><td></td><td>0,4</td><td>-2 1,2</td></tr></table>

<table><tr><td rowspan="3"></td><td>Sum</td><td colspan="5">-2,4</td></tr><tr><td rowspan="2">Rank of Req.</td><td colspan="5">30</td></tr><tr><td>User</td><td>Restaurant owner</td><td>Administrator</td><td colspan="2">Customer</td></tr><tr><td rowspan="8">QR16</td><td>Magnus</td><td>-2</td><td>-2</td><td>0</td><td colspan="2">-1</td></tr><tr><td>Elmira</td><td></td><td>-1</td><td>0</td><td colspan="2">2</td></tr><tr><td>Niclas</td><td>222</td><td></td><td></td><td colspan="2"></td></tr><tr><td></td><td></td><td>-2</td><td>1</td><td colspan="2">2</td></tr><tr><td>Faegheh</td><td>-2</td><td>-2</td><td>1</td><td colspan="2">0</td></tr><tr><td>Sarah</td><td></td><td>-2</td><td>0</td><td colspan="2">0</td></tr><tr><td>Average Sum</td><td>-2</td><td>-1,8</td><td>0,4</td><td colspan="2">0,6</td></tr><tr><td>Rank of</td><td></td><td></td><td></td><td colspan="2">-2,8</td></tr><tr><td rowspan="9">QR17</td><td>Req.</td><td></td><td>33</td><td></td><td colspan="2"></td></tr><tr><td></td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td colspan="2">Customer</td></tr><tr><td>Magnus</td><td>2</td><td>-2</td><td>-2</td><td colspan="2">0</td></tr><tr><td>Elmira Niclas</td><td>1</td><td>-2</td><td>-2</td><td colspan="2">2</td></tr><tr><td></td><td>1</td><td>22</td><td></td><td colspan="2">2</td></tr><tr><td>Faegheh</td><td>0</td><td></td><td>222</td><td colspan="2">1</td></tr><tr><td>Sarah</td><td>0</td><td>-2</td><td></td><td colspan="2">1</td></tr><tr><td>Average</td><td>0,8</td><td>-2</td><td>-2</td><td colspan="2">1,2</td></tr><tr><td>Sum Rank of</td><td></td><td></td><td></td><td colspan="2">-2</td></tr><tr><td>Req.</td><td></td><td></td><td>22</td><td colspan="3"></td></tr><tr><td rowspan="10">QR18</td><td>Magnus</td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td colspan="2">Customer</td></tr><tr><td>Elmira</td><td>-2</td><td>2</td><td>-2</td><td colspan="2">0</td></tr><tr><td>Niclas</td><td></td><td>1</td><td></td><td colspan="2">2</td></tr><tr><td>Faegheh</td><td>222</td><td>1</td><td>2222</td><td colspan="2">2</td></tr><tr><td>Sarah</td><td></td><td>0</td><td></td><td colspan="2">1</td></tr><tr><td></td><td>-2</td><td>0</td><td></td><td colspan="2">1</td></tr><tr><td>Average</td><td>-2</td><td>0,8</td><td>-2</td><td colspan="2">1,2</td></tr><tr><td>Sum Rank of</td><td></td><td></td><td></td><td colspan="2">-2</td></tr><tr><td>Req.</td><td></td><td>23</td><td></td><td colspan="2"></td></tr><tr><td></td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td colspan="2"></td></tr><tr><td rowspan="10">QR19</td><td></td><td></td><td></td><td></td><td colspan="2">Customer</td></tr><tr><td>Magnus</td><td>-2</td><td>-2</td><td>-2</td><td colspan="2">2</td></tr><tr><td>Elmira</td><td>-1</td><td>-1</td><td></td><td colspan="2">2</td></tr><tr><td>Niclas</td><td>-2</td><td>-2</td><td>222</td><td colspan="2">1</td></tr><tr><td>Faegheh</td><td>-2</td><td>-2</td><td></td><td colspan="2"></td></tr><tr><td>Sarah</td><td>-1</td><td></td><td>-2</td><td colspan="2">2</td></tr><tr><td></td><td></td><td>-1</td><td></td><td colspan="2">1</td></tr><tr><td>Average</td><td>-1,6</td><td>-1,6</td><td>-2</td><td colspan="2">1,6</td></tr><tr><td>Sum Rank of</td><td></td><td></td><td></td><td colspan="2">-3,6</td></tr><tr><td>Req.</td><td></td><td>40</td><td></td><td colspan="2"></td></tr><tr><td rowspan="5">QR20</td><td>Magnus Elmira</td><td rowspan="5"></td><td>Restaurant owner</td><td>Administrator</td><td colspan="2">Customer</td></tr><tr><td></td><td>User 0</td><td>-2</td><td colspan="2">22222</td></tr><tr><td></td><td>0</td><td></td><td colspan="2">2 2</td></tr><tr><td>Niclas</td><td>1</td><td>-2 -2</td><td colspan="2">1</td></tr><tr><td>Faegheh</td><td>1 -1</td><td>-2 -1</td><td colspan="2">1</td></tr><tr><td rowspan="4"></td><td>Average</td><td>0,2</td><td>-1,8</td><td>-2</td><td>1,4</td></tr><tr><td>Sum</td><td colspan="4">-2,2</td></tr><tr><td>Rank of Req.</td><td colspan="4"></td></tr><tr><td></td><td></td><td>27 Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td rowspan="11">QR21</td><td></td><td>User</td><td></td><td></td><td></td></tr><tr><td>Magnus</td><td>-2 -1</td><td>-2</td><td>-2</td><td>2</td></tr><tr><td>Elmira</td><td></td><td>1221</td><td></td><td>2</td></tr><tr><td>Niclas</td><td>-2</td><td></td><td>11221</td><td>2</td></tr><tr><td>Faegheh</td><td>1</td><td></td><td></td><td>2</td></tr><tr><td>Sarah</td><td>-1</td><td></td><td></td><td>2</td></tr><tr><td>Average Sum</td><td>-1</td><td>-1,6</td><td>-1,6</td><td>2 -2,2</td></tr><tr><td>Rank of</td><td colspan="5"></td></tr><tr><td>Req.</td><td colspan="5">28</td></tr><tr><td rowspan="10">QR23</td><td>Magnus</td><td>User</td><td>Restaurant owner</td><td>Administrator</td><td>Customer</td></tr><tr><td>Elmira</td><td>1 1</td><td>-2</td><td>22222</td><td>1</td></tr><tr><td>Niclas</td><td>1</td><td>0</td><td></td><td>2</td></tr><tr><td></td><td></td><td>221</td><td></td><td>1</td></tr><tr><td>Faegheh</td><td>1</td><td></td><td></td><td>1</td></tr><tr><td>Sarah</td><td>1</td><td></td><td></td><td>1</td></tr><tr><td>Average</td><td>1</td><td>-1,4</td><td>-2</td><td>1,2</td></tr><tr><td>Sum</td><td></td><td></td><td></td><td>-1,2</td></tr><tr><td>Rank of Req.</td><td colspan="4">15</td></tr></table>

Table 8 – Result of five-way priority scheme prioritization
<table><tr><td>Priority</td><td>Requirement ID</td></tr><tr><td>11</td><td>FR30</td></tr><tr><td>12</td><td>FR28</td></tr><tr><td>13</td><td>FR29</td></tr><tr><td>14</td><td>FR32</td></tr><tr><td>15</td><td>FR11</td></tr><tr><td>16</td><td>FR22</td></tr><tr><td>17</td><td>FR31</td></tr><tr><td>18</td><td>FR9</td></tr><tr><td>19</td><td>QR13</td></tr><tr><td>20</td><td>QR1</td></tr><tr><td>21</td><td>QR2</td></tr><tr><td>22</td><td>QR14</td></tr><tr><td></td><td></td></tr><tr><td>23</td><td>FR1</td></tr><tr><td>24</td><td>FR23</td></tr><tr><td>25</td><td>QR23</td></tr><tr><td>26</td><td>FR26</td></tr><tr><td>27</td><td>FR13</td></tr><tr><td>28</td><td>FR12</td></tr><tr><td>29</td><td>QR4</td></tr><tr><td>30</td><td>QR5</td></tr></table>

<table><tr><td rowspan=1 colspan=1>31</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>QR3</td></tr><tr><td rowspan=1 colspan=1>32</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>QR17</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>33</td><td rowspan=1 colspan=3>QR18</td></tr><tr><td rowspan=1 colspan=1>34</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>FR15</td></tr><tr><td rowspan=1 colspan=1>35</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>FR18</td></tr><tr><td rowspan=1 colspan=1>36</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>QR8</td></tr><tr><td rowspan=1 colspan=1>37</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>QR20</td></tr><tr><td rowspan=1 colspan=1>38</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>QR21</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>39</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>FR3</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>40</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>QR15</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>41</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>FR16</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>42</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>FR20</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>43</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>QR16</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>44</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>FR2</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>45</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>FR17</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>46</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>FR10</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>47</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>FR14</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>48</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>FR19</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>49</td><td rowspan=1 colspan=3>FR25</td></tr><tr><td rowspan=1 colspan=1>50</td><td rowspan=1 colspan=3>QR19</td></tr><tr><td rowspan=1 colspan=1>51</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>FR4</td></tr><tr><td rowspan=1 colspan=1>52</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>FR5</td></tr><tr><td rowspan=1 colspan=1>53</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=2>FR21</td></tr><tr><td rowspan=1 colspan=1>54</td><td rowspan=1 colspan=3>FR33</td></tr><tr><td rowspan=1 colspan=1>55</td><td rowspan=1 colspan=3>QR10</td></tr><tr><td rowspan=1 colspan=1>56</td><td rowspan=1 colspan=3>QR11</td></tr></table>

## Appendix IV: Release Plan

Table 9 – Release plan
<table><tr><td colspan="1" rowspan="1">RE:</td><td colspan="1" rowspan="1">Dependencies</td><td colspan="1" rowspan="1">Description</td><td colspan="1" rowspan="1">Motivation</td><td colspan="1" rowspan="1">Release</td><td colspan="1" rowspan="1">Duration</td></tr><tr><td colspan="1" rowspan="1">FR1</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Downloadmobileapplication</td><td colspan="1" rowspan="1">This requirement makes theapplication available for users and istherefore an important requirement toinclude in the first release.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">80</td></tr><tr><td colspan="1" rowspan="1">FR2</td><td colspan="1" rowspan="1">FR1</td><td colspan="1" rowspan="1">Download andnotify users ofnew releases</td><td colspan="1" rowspan="1">The download of the new versions isimportant for users to be able toreceive the future release of theapplication and will therefore beincluded in the first release.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">FR3</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Userregistration</td><td colspan="1" rowspan="1">For the user to be able to use theapplication, the user has to registrant.Consequently, this requirement needsto be met in the first release.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">4</td></tr><tr><td colspan="1" rowspan="1">FR4</td><td colspan="1" rowspan="1">FR1, FR3</td><td colspan="1" rowspan="1">User Log-in</td><td colspan="1" rowspan="1">For the user to be able to use theapplication, the user has to log in.Consequently, this requirement needsto be met in the first release</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">FR5</td><td colspan="1" rowspan="1">FR1</td><td colspan="1" rowspan="1">RetrievePassword</td><td colspan="1" rowspan="1">For the user to be able to receive aforgotten password will have to waitto the second release. This is not vitalfor the application and was thereforenot included in the first release.</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR6</td><td colspan="1" rowspan="1">FR4</td><td colspan="1" rowspan="1">Search</td><td colspan="1" rowspan="1">The search feature is one of the mostimportant and vital part of thesystem. It's part of the basic goal ofthe program and should therefore beincluded in the first release</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">FR7</td><td colspan="1" rowspan="1">FR6, QR22,QR23</td><td colspan="1" rowspan="1">Search result ina map view</td><td colspan="1" rowspan="1">The ability to show the search resultin a map view is part of the basicgoal of the program and shouldtherefore be included in the firstrelease.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR8</td><td colspan="1" rowspan="1">FR6, QR22</td><td colspan="1" rowspan="1">Search result ina list view</td><td colspan="1" rowspan="1">The ability to show the search resultin a list view is part of the basic goal</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">of the program. We have decided toput this one in the second release andonly include the map result view inthe first release.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">FR9</td><td colspan="1" rowspan="1">FR7, FR8</td><td colspan="1" rowspan="1">Navigation torestaurant</td><td colspan="1" rowspan="1">To make the first release interestingand useful for the users, this isincluded in the first release.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">FR10</td><td colspan="1" rowspan="1">FR7, FR8</td><td colspan="1" rowspan="1">Switch resultview</td><td colspan="1" rowspan="1">The switch between the result viewswill be implemented after the resultlist is implemented. This is not insome way vital for the applicationand can be discarded if the projectgets delayed or overruns the budget.</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR11</td><td colspan="1" rowspan="1">FR7, FR8</td><td colspan="1" rowspan="1">Selecting theinformationlink</td><td colspan="1" rowspan="1">This will be added as an additionalfeature in the second release to makethe application more attractive for theusers.</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR12</td><td colspan="1" rowspan="1">FR8</td><td colspan="1" rowspan="1">Search by price</td><td colspan="1" rowspan="1">This will be added as an additionalfeature in the third release to makethe application more attractive for theusers.</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR13</td><td colspan="1" rowspan="1">FR7</td><td colspan="1" rowspan="1">Search bydestination</td><td colspan="1" rowspan="1">This is the search function that willbe included in the first release.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR14</td><td colspan="1" rowspan="1">FR12, FR13</td><td colspan="1" rowspan="1">Accepted inputfor price anddestinationsearch</td><td colspan="1" rowspan="1">This is a requirement that will makethe application more stable. It will beadded in the third release.</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR15</td><td colspan="1" rowspan="1">FR7</td><td colspan="1" rowspan="1">Search byrestaurant type</td><td colspan="1" rowspan="1">This will be added as an additionalfeature to the second release to makethe application more attractive for theusers.</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">3</td></tr><tr><td colspan="1" rowspan="1">FR16</td><td colspan="1" rowspan="1">FR7</td><td colspan="1" rowspan="1">Search byspecific dish</td><td colspan="1" rowspan="1">This will be added as an additionalfeature in the third release to makethe application more attractive for theusers.</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">3</td></tr><tr><td colspan="1" rowspan="1">FR17</td><td colspan="1" rowspan="1">FR6</td><td colspan="1" rowspan="1">Free-textsearch</td><td colspan="1" rowspan="1">This will be added as an additionalfeature to the first release to make theapplication more attractive for the</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">3</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">users.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">FR18</td><td colspan="1" rowspan="1">FR5</td><td colspan="1" rowspan="1">No searchmatch found</td><td colspan="1" rowspan="1">This is a requirement that will makethe application more stable and makethe user experience better. It is notvital and will be added in the thirdrelease.</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR19</td><td colspan="1" rowspan="1">FR8</td><td colspan="1" rowspan="1">Sorting results</td><td colspan="1" rowspan="1">This will be added as an additionalfeature to the first release to make theapplication more attractive for theusers.</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">FR20</td><td colspan="1" rowspan="1">FR7, FR8</td><td colspan="1" rowspan="1">Filteringresults</td><td colspan="1" rowspan="1">This will be added as an additionalfeature to the first release to make theapplication more attractive for theusers.</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">4</td></tr><tr><td colspan="1" rowspan="1">FR21</td><td colspan="1" rowspan="1">FR1</td><td colspan="1" rowspan="1">Profile page</td><td colspan="1" rowspan="1">This will be added as an additionalfeature in the third release to makethe application more attractive for theusers.</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR22</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Create account- restaurantowner</td><td colspan="1" rowspan="1">The restaurant owner is a vital part ofthe system and must be included inthe first release.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">FR23</td><td colspan="1" rowspan="1">FR27</td><td colspan="1" rowspan="1">Log-in -restaurantowner</td><td colspan="1" rowspan="1">This should be included in the firstrelease because the restaurant ownerneeds to be able to log in so hi/shecan manage the restaurantinformation.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">FR24</td><td colspan="1" rowspan="1">FR23, FR25</td><td colspan="1" rowspan="1">Manage info -restaurantowner</td><td colspan="1" rowspan="1">The ability for the restaurant ownerto manage the information about therestaurant is very important, if thereis no information there is nothing tosearch for.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">FR25</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Selectingpreferredlanguage onthe web-portal- restaurantowner</td><td colspan="1" rowspan="1">This will be added as an additionalfeature in the third release to makethe application more attractive for theusers. It is not vital for theapplication and will therefore beimplemented in the third release,</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">3</td></tr><tr><td colspan="1" rowspan="1">FR26</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Log-in - admin</td><td colspan="1" rowspan="1">This should be included in the firstrelease because the administratorneeds to be able to log in so she/hican manage the system.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">FR27</td><td colspan="1" rowspan="1">FR26, FR22</td><td colspan="1" rowspan="1">Verifyrestaurantowner</td><td colspan="1" rowspan="1">It's important for the admin to be ableto verify the restaurant owner'sapplication for registration.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">FR28</td><td colspan="1" rowspan="1">FR26</td><td colspan="1" rowspan="1">Manage rest.types -administrator</td><td colspan="1" rowspan="1">The type search will be added in thesecond release.</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR29</td><td colspan="1" rowspan="1">FR26</td><td colspan="1" rowspan="1">Manage rest.dished -administrator</td><td colspan="1" rowspan="1">The dish search will be added in thesecond release.</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR30</td><td colspan="1" rowspan="1">FR26</td><td colspan="1" rowspan="1">Manage rest.info -administrator</td><td colspan="1" rowspan="1">The info link will be added in thesecond release.</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR31</td><td colspan="1" rowspan="1">FR26</td><td colspan="1" rowspan="1">Manage users -administrator</td><td colspan="1" rowspan="1">The administrator needs to be able tohandle users during the first release.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR32</td><td colspan="1" rowspan="1">FR26</td><td colspan="1" rowspan="1">Selectingpreferredlanguage onthe web-portal- administrator</td><td colspan="1" rowspan="1">The administrator needs to be able tohandle restaurant owners during thefirst release.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">FR33</td><td colspan="1" rowspan="1">FR26</td><td colspan="1" rowspan="1">Languageselection onportal</td><td colspan="1" rowspan="1">This will be added as an additionalfeature in the third release to makethe application more attractive for theusers. It is not vital for theapplication and will therefore beimplemented in the third release.</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">QR1</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Prominentsearch feature</td><td colspan="1" rowspan="1">This is a very high-prioritizedrequirement. Consequently, this willbe included in the first release.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">QR2</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">The ease ofusage of thesearch feature</td><td colspan="1" rowspan="1">This is a very high-prioritizedrequirement. Consequently, this willbe included in the first release.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">QR3</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">The ease ofusage of theresult in the listview</td><td colspan="1" rowspan="1">This is a high-prioritizedrequirement. But we have decided toput this in the second release in favorfor more vital and higher prioritizedrequirements.</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">QR4</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">The ease ofusage of theresult in mapview</td><td colspan="1" rowspan="1">This is a high-prioritizedrequirement. But we have decided toput this in the second release in favorfor more vital and higher prioritizedrequirements.</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">QR5</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">The ease ofusage of theinformationlink</td><td colspan="1" rowspan="1">This will be considered when all themandatory requirements for thesystem have been implemented.</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">QR6</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Systemresponse time</td><td colspan="1" rowspan="1">This will be considered andcontinuously improved during thewhole process. We can onlydischarge the requirement when allfunctions are implemented.</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">*</td></tr><tr><td colspan="1" rowspan="1">QR7</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Systemavailability</td><td colspan="1" rowspan="1">This will be considered andcontinuously improved during thewhole process.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">*</td></tr><tr><td colspan="1" rowspan="1">QR8</td><td colspan="1" rowspan="1">QR22, QR23,FR14, FR15,FR16, FR17</td><td colspan="1" rowspan="1">Systemdependability</td><td colspan="1" rowspan="1">This will be considered andcontinuously improved during thewhole process. We can onlydischarge the requirement when allfunctions are implemented.</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">*</td></tr><tr><td colspan="1" rowspan="1">QR9</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Systemreliability</td><td colspan="1" rowspan="1">This will be considered andcontinuously improved during thewhole process.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">*</td></tr><tr><td colspan="1" rowspan="1">QR10</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Applicationhard drivespace usage</td><td colspan="1" rowspan="1">This will be considered andcontinuously improved during thewhole process. We can onlydischarge the requirement when allfunctions are implemented.</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">*</td></tr><tr><td colspan="1" rowspan="1">QR11</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Applicationmemory usage</td><td colspan="1" rowspan="1">This will be considered andcontinuously improved during thewhole process. We can only</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">*</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">discharge the requirement when allfunctions are implemented.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">QR12</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Communication security</td><td colspan="1" rowspan="1">As the system grows, and withrespect for the users this need to beincluded.</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">4</td></tr><tr><td colspan="1" rowspan="1">QR13</td><td colspan="1" rowspan="1">FR22</td><td colspan="1" rowspan="1">Non-existingaccountsecurity forrest. Owners</td><td colspan="1" rowspan="1">This need to be included in the firstrelease to enhance the safety of thesystem.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">3</td></tr><tr><td colspan="1" rowspan="1">QR14</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Non-existingaccountsecurity for theadministrators</td><td colspan="1" rowspan="1">This needs to be included in the firstrelease to enhance the safety of thesystem.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">3</td></tr><tr><td colspan="1" rowspan="1">QR15</td><td colspan="1" rowspan="1">FR23</td><td colspan="1" rowspan="1">Log in securityfor rest.Owners</td><td colspan="1" rowspan="1">This needs to be included in the firstrelease to prevent illegitimateattempts to use the restaurantsowners account.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">3</td></tr><tr><td colspan="1" rowspan="1">QR16</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Log in securityforadministrators</td><td colspan="1" rowspan="1">This need to be included in the firstrelease to prevent illegitimateattempts to use the administratoraccount.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">QR17</td><td colspan="1" rowspan="1">FR3</td><td colspan="1" rowspan="1">User accountcreationsecurity</td><td colspan="1" rowspan="1">This needs to be included in the firstrelease to resolve conflict betweenusers with the same name.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">QR18</td><td colspan="1" rowspan="1">FR22</td><td colspan="1" rowspan="1">Restaurantowner accountcreationsecurity</td><td colspan="1" rowspan="1">This needs to be included in the firstrelease to resolve conflict betweenrestaurant owners with the samename.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">QR19</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Applicationextendibility</td><td colspan="1" rowspan="1">This will be considered andcontinuously improved duringdevelopment.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">*</td></tr><tr><td colspan="1" rowspan="1">QR20</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Applicationportability</td><td colspan="1" rowspan="1">This will be considered andcontinuously improved during thewhole process.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">50</td></tr><tr><td colspan="1" rowspan="1">QR21</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Applicationtestability</td><td colspan="1" rowspan="1">The test environment for the systemwill continuously be built as the</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">30</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">system expands.</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">QR22</td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">Internetconnection</td><td colspan="1" rowspan="1">Internet connection is mandatory forthe application to work and istherefore included in the first release.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">*</td></tr><tr><td colspan="1" rowspan="1">QR23</td><td colspan="1" rowspan="1">一</td><td colspan="1" rowspan="1">GPSconnection</td><td colspan="1" rowspan="1">GPS connection is mandatory for theapplication to be able to show theresult and is therefore included in thefirst release.</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">2</td></tr></table>

![](images/3fbf5b1ec52206037e628e7a654f92b41a53d324f130aa879ba436df2bb39d93.jpg)  
Figure 11 – Release plan schedule

![](images/2df0f3c3d413285462eae801f6d2c5e98df4623b57aec8936fd1e8f8a12d453b.jpg)  
Figure 12 – SD diagram

![](images/54cb5de735c810b34ba4a36a7decbebe71e671c5784c2afabc1ec8c6702d2ecb.jpg)  
Figure 13 – SR diagram