===================
Extensions Examples
===================

Extension PlantUML Examples
===========================

.. uml::

   Alice -> Bob: Hi!
   Alice <- Bob: How are you?

Extensions imgmath Examples
===========================

Since Pythagoras, we know that :math:`a^2 + b^2 = c^2`.

.. math::

   SPEZ = \frac{d}{{b + d}}

   (a + b)^2 = a^2 + 2ab + b^2

   (a - b)^2 = a^2 - 2ab + b^2


..    digraph packages_mosaik {
    charset="utf-8"
    rankdir=BT
    "0" [label="mosaik", shape="box"];
    "1" [label="mosaik._debug", shape="box"];
    "2" [label="mosaik._version", shape="box"];
    "3" [label="mosaik.exceptions", shape="box"];
    "4" [label="mosaik.scenario", shape="box"];
    "5" [label="mosaik.scheduler", shape="box"];
    "6" [label="mosaik.simmanager", shape="box"];
    "7" [label="mosaik.util", shape="box"];
    "0" -> "0" [arrowhead="open", arrowtail="none"];
    "0" -> "2" [arrowhead="open", arrowtail="none"];
    "0" -> "4" [arrowhead="open", arrowtail="none"];
    "1" -> "0" [arrowhead="open", arrowtail="none"];
    "1" -> "5" [arrowhead="open", arrowtail="none"];
    "4" -> "0" [arrowhead="open", arrowtail="none"];
    "4" -> "1" [arrowhead="open", arrowtail="none"];
    "4" -> "3" [arrowhead="open", arrowtail="none"];
    "4" -> "5" [arrowhead="open", arrowtail="none"];
    "4" -> "6" [arrowhead="open", arrowtail="none"];
    "4" -> "7" [arrowhead="open", arrowtail="none"];
    "5" -> "3" [arrowhead="open", arrowtail="none"];
    "5" -> "6" [arrowhead="open", arrowtail="none"];
    "6" -> "0" [arrowhead="open", arrowtail="none"];
    "6" -> "2" [arrowhead="open", arrowtail="none"];
    "6" -> "3" [arrowhead="open", arrowtail="none"];
    "6" -> "7" [arrowhead="open", arrowtail="none"];
    "7" -> "3" [arrowhead="open", arrowtail="none"];
    }
    @enduml
