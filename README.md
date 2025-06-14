# Robot Herb Estimation Project

We're programming the [farm-ng Amiga](https://farm-ng.com/amiga/) to estimate herb harvest yields using [ToF cameras](https://shop.luxonis.com/products/oak-d-sr-poe?variant=46456301027551). [Preliminary experiments](https://thevanadium.github.io/portfolio/2024-08-Fall-CSE-302-poster.pdf) show our system is promising. If you'd like to contribute, check out [CONTRIBUTING.md](https://github.com/TheVanadium/farm-ng-amiga-autonomous-navigation/blob/master/CONTRIBUTING.md).

## The Code

We have code that does a number of things necessary for herb yield estimation. For more detail, check out their respective READMEs.

#### `amiga-app/`
The Amiga app that takes pictures of the cilantro.

#### `data_analysis/`
Code that analyzes point clouds of herb crops to estimate its weight

#### `multi-cam-calibration/`
Code that calibrates the cameras for point cloud combination

## Our Collaborators
A big thanks to the people and organizations we've collaborated with:
- [farm-ng](https://farm-ng.com/)
- [Innovate To Grow](https://i2g.ucmerced.edu/)
- [SupHerb Farms](https://supherbfarms.com/)
- [UC Merced Environmental Smart Farm](https://vista.ucmerced.edu/farm/)
