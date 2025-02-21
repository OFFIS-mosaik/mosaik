===========
Tiered Time
===========

.. currentmodule:: mosaik.tiered_time

Tiered times and tiered durations are at the core of mosaik's internal time handling.
However, as a user of mosaik, you will usually not deal with them directly, and instead use simulator groups and weak connection, see :doc:`/tutorials/sametimeloops`.
Still, we explain them here for people who are just curious or who are working on mosaik itself.
Tiered durations are also the content of our paper `Tiered Durations: Scheduling at Differing Time Resolutions <https://www.offis.de/offis/publikation/tiered-durations-scheduling-at-differing-time-resolutions.html>`_.

The motivation for introducing tiered times is given in :doc:`/tutorials/sametimeloops`.

The central decision in the design is that simulators that are not involved in the faster communication loops should not need to concern themselves with the finer substeps produced by these loops.
To facilitate this, every simulator in a mosaik simulation is assigned a resolution :math:`n`, meaning that time stamps assigned to steps of that simulator will have :math:`n` components, which we call **tiers**.
(This is different from the time resolution of the scenario, which specifies the relation between mosaik steps and seconds.)
Such a multi-component time stamp is called a **tiered time**, and the number :math:`n` of tiers is its **length**.
In the code, tiered times are represented by the :class:`TieredTime` class.

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

The first trick is that a simulator that only ever runs at the main steps should not even *need to know* about the substeps.
This is why simulators are allowed to run at different resolutions.
When a time it transferred to a simulator at a lower resolution, the extra tiers are simply discarded.
Due to mosaik's general scheduling rules, this simulator will then wait until all the substeps for the main step have happened.
It will only step once the simulators providing its input have progress *past* its own time; and because the simulator does not get to see the substeps, this only happens once all of them have happened.

The second trick relates to how these more complex delays are combined.

Why is this necessary?
Well, to do its scheduling, mosaik not only considers the direct connections between two simulators, but will occasionally also need to consider indirect connections.
By having delays that can be combined nicely, mosaik can still assign a combined delay to these indirect connections.

So, **tiered durations**, which is what we call the datatype of these delays, are not just a tuple of numbers representing the delay at each tier.
They do have this, but additionally, there is an index called the **cut-off**.
We write a tiered duration like :math:`(1, 2 | 3, 4)` with the vertical bar indicating the position of the cut-off.
In the code, tiered durations are represented by the :class:`TieredDuration` class.

When adding a tiered duration to something (a tiered time or another tiered duration), all the tiers before the cut-off are actually added to the corresponding tier of the something.
However, the tiered duration's tiers beyond the cut-off simply replace the remaining tiers of the something.
When adding the tiered duration to a tiered time, the result is another tiered time.
When adding two tiered durations, the result is a tiered duration, and its cut-off is the minimum cut-off of the two summands.

The following is an example of the addition of two tiered durations.
Note how the the last two tiers of the result are simply given by the last two components of the second summand, as they lie after the second summand's cut-off.
The result has the length of the second summand; however, in this case, the result's cut-off is determined by the first summand, as it has the smaller cut-off.

.. math::

     & ~( & 10 & , & ~20 & | & ~30 & , & ~40 & ) & \\
   + & ~( &  1 & , &  ~2 & , &  ~3 & | &   4 & , & ~5) \\
   = & ~( & 11 & , & ~22 & | & ~33 & , &   4 & , &  5)

The addition of tiered durations is associative (and the duration of all zeros and a maximal cut-off is the neutral element), but it is not commutative.

Tiered durations can be ordered in a limited way.
Namely, tiered duration :math:`u` is shorter than tiered duration :math:`v` if it is either lexicographically smaller in the part before either of them is cut off, or if it is smaller lexicographically overall *and* its cut-off is smaller.
This slightly cumbersome definition is necesarry to get a reasonable interaction with addition.
Namely, we get that when :math:`s` and :math:`t` are tiered times with :math:`s \leq t`, and :math:`u` and :math:`v` are tiered durations with :math:`u \leq v`, then :math:`s + u \leq t + v`, as one would expect.

The definition of the order has the consequence that not every (non-empty) finite set of tiered durations has a unique minimal element.
In fact, there can be as many minimal elements as there are tiers in the tiered durations.
For this reason, mosaik sometimes need to store not just one tiered duration for a connection, but several.
(As there are rarely more than 2 or 3 tiers, this is still manageable.)
For bookeeping, we have the :class:`MinimalDurations` class.
It just stores the minimal elements of all those added to it.
For example, if you add :math:`(0 | 2)` and :math:`(0, 1|)`, both will be stored as they are incomparable.
If you try to add :math:`(0 | 3)`, nothing will happens, as it is bigger than the already-included :math:`(0 | 2)`.
And finally, if you add :math:`(0 | 0)`, it will replace both elements, as it is smaller than either of them.
