1.4.1 (2026-08-25)
------------------

* Fix the comments written before the ``PVTTABLE LABEL`` keyword of the generated ``.tab`` PVT tables, which made ALFAsim fail to read the file with ``Unknown PVT Table input file format!``. The comments are now written after the keywords of the header, and the tables already generated are put in the accepted order when they are written again.


1.4.0 (2026-08-03)
------------------

* Include script and CLI (``alfasim-score-fix-pvt-table``) to check and fix ``.tab`` PVT tables delivered by WELLBOREPROPS that write zeroed properties for phases that do not exist.
* Fix wellbore/node PVT model on the converted alfacase to use the ``base`` PVT table.


1.3.1 (2026-06-19)
------------------

* Update ``alfasim-sdk`` dependency to 1.6.0 and migrate to the ``generate_alfacase_file`` API.
* Drop support for Python 3.8 and 3.9 (``alfasim-sdk`` requires Python >= 3.10).


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
