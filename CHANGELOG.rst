1.2.2 (2026-06-19)
------------------

* Update ``alfasim-sdk`` dependency to 1.6.0.


1.2.1 (2026-06-19)
------------------

* Fix output results JSON dropping annuli MDs beyond the annulus end and emitting ``volume.diff`` as a scalar.


1.2.0 (2026-06-10)
------------------

* Include support to simulation regime input.


1.1.1 (2026-03-19)
------------------

* Ignore walls with NaN or negative dummy values from ALFAsim output to build output results JSON layers.

1.1.0 (2026-02-20)
------------------

* Update the alfacase converter to support ALFAsim APB plugin v2025.2.1
* Update convert to improve ALFAsim simulation performance:
  * Use Zamora correlation for PVT table input
  * Periodic calculation for APB
  * Update of thermal properties only in initalization

1.0.0 (2025-04-11)
------------------

* Update the alfacase converter to create files compatible with ALFAsim APB plugin v1.0.1
* Add new converter for pvt tables from wellprops to `.tab` format

0.2.0 (2024-12-18)
------------------

* Improvements on API.
* Add documentation on how to use the API.


0.1.0 (2024-06-10)
------------------

* First release on PyPI.
