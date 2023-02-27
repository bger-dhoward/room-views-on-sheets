# Room Views On Sheets

A pyRevit tool for automatically creating enlarged plan, RCP, interior elevations, and 3D axon for selected rooms, then placing on sheets.

Originally developed for NYP CC team, February 2023

Uses method for cropping 3D views via transforms of max/min edge points. Pretty much just copied exactly from Jeremy Tammik's [2009 article on The Building Coder](https://thebuildingcoder.typepad.com/blog/2009/12/crop-3d-view-to-room.html), revised for 2023 API and Python.