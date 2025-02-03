===========
Tiered Time
===========

Tiered times and tiered durations are at the core of mosaik's internal time handling.
However, as a user of mosaik, you will usually not deal with them directly, and instead use simulator groups and weak connection, see :doc:`/tutorials/sametimeloops`.
Still, we explain them here for people who are just curious or who are working on mosaik itself.

The motivation for introducing tiered times is given in :doc:`/tutorials/sametimeloops`.

The central decision in the design is that simulators that are not involved in the faster communication loops should not need to concern themselves with the finer substeps produced by these loops.
To facilitate this, every simulator in a mosaik simulation is assigned a time resolution :math:`n`, meaning that time stamps assigned to steps of that simulator will have :math:`n` components, which we call **tiers**.
(This is different from the time resolution of the scenario, which specifies the relation between mosaik steps and seconds.)
Such a multi-component time stamp is called a **tiered time**, and the number :math:`n` of tiers is its **length**.

For a single simulator, its time stamps are simply ordered lexicographically.
This has the consequence that between any two steps at one level, there are infinitely many steps at the next level down.
For example, between the two tiered times :math:`(2, 0)` and :math:`(3, 0)`, there are the steps :math:`(2,1), (2,2), (2,3), (2,4), \dots`

This type of time exists in other co-simulation frameworks as well, for example as *super-dense time*.

The real challenge comes from relating these times for different simulators.
The naive approach would be to simply pick a number :math:`n` of tiers for the entire simulation and to represent delays :math:`n`-tuples as well, adding componentwise.
However, this runs into the following problem:
Say we picked :math:`n = 2` and one of the simulators is supposed to run at the main steps :math:`(0, 0), (1, 0), (2, 0)`, etc.
It is part of a normal, time-shifted feedback loop, where its input from some other simulator is delayed by one entire time step (which would be a delay of :math:`(1, 0)`).
If this other simulator *does* perform substeps, *its* relevant output might be produced at a time like :math:`(0, 3)`, which after applying the time shift would reach the first simulator at :math:`(1, 3)`, which is too late for its :math:`(1, 0)` step!
We also cannot change the delay to be something like :math:`(1, -3)` because the number of substeps taken might not always be the same.
(Also, it would be annoying to have to figure this out beforehand.)
