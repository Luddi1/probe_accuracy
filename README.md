Probe Accuracy Testing
======================

This is for testing the accuracy of the toolhead probe on a 3D printer running Klipper.  There are two parts
to this test:

1. a macro to run the test
2. a Python script to collect the results and create a chart

Installation
------------

Create a Python environment for this script.  Use ssh to log in to the Raspberry Pi, and run the following:

    sudo apt install python3-venv
    python3 -m venv /home/pi/plotly-env
    /home/pi/plotly-env/bin/pip install -U plotly
    mkdir /home/pi/probe_accuracy

Download `probe_accuracy.py` from this repository and copy it into `/home/pi/probe_accuracy/` on the Raspberry Pi.

Download `test_probe_accuracy.cfg` from this repository and copy it to the directory containing your
`printer.cfg` - it's `/home/pi/klipper_config/` if you're using
[MainsailOS](https://github.com/raymondh2/MainsailOS).  Edit your `printer.cfg` and add the
following on a new line:

    [include test_probe_accuracy.cfg]

Restart Klipper.

Test Execution
--------------

Home and level your printer (G32 on a [VORON 2](https://vorondesign.com)).  Position the nozzle over the bed
where you want to test the probe, probably in the center of the bed.  Use ssh to log in to the Raspberry
Pi and run the following to start the data collection:

    /home/pi/plotly-env/bin/python3 /home/pi/probe_accuracy/probe_accuracy.py

**IMPORTANT**:  Leave that ssh session/window open for the duration of the test.

Alternatively, if you don't want to leave the window open, or have a bad network connection to the Pi, you
can run the script in the background, and then you don't have to leave the ssh session open:

    nohup /home/pi/plotly-env/bin/python3 /home/pi/probe_accuracy/probe_accuracy.py >/tmp/probe_accuracy.log 2>&1 &

Run the test macro on the printer:

    TEST_PROBE_ACCURACY

It will continuously run `PROBE_ACCURACY` while heating up the bed, soaking the bed, heating up the hotend, and
soaking the hotend.  See below if you want to change the temperatures or soak times.  The default will heat the
bed to 110, soak for 30 minutes, then heat the hotend to 240, and soak for 15 minutes - so this test will
probably take over an hour to run.  Get some coffee while you wait.

After the test is complete, the printer will raise the toolhead a little and turn off the heaters.  The chart
output should be on the Raspberry Pi in `/tmp/probe_accuracy.html` - copy that file to your local machine and
open it.  It should contain a chart showing the Z height over time, as the bed and the hotend heat up.  There's
also a `/tmp/probe_accuracy.json` file generated on the Raspberry Pi, which contains the data used for the chart.
You can download it and use it to create your own chart if you wish.

All thermistors defined in your `printer.cfg` are plotted on the chart.  Once the chart is opened, you can click
on the legend of any thermistor in the chart to turn the trace on or off.

Plotting Existing Data
----------------------

If you already have a JSON data file and want to generate a chart from it, you can use the `--plot-only` option.

    /home/pi/plotly-env/bin/python3 /home/pi/probe_accuracy/probe_accuracy.py \
        --plot-only \
        --data-file /tmp/probe_accuracy.json \
        --chart-file /tmp/probe_accuracy.html

Customizing The Test
--------------------

You can pass parameters to the macro to change the temperatures, soak times and dwell behavior:

    TEST_PROBE_ACCURACY [START_IDLE_MINUTES=<value>]
                        [BED_TEMP=<value>] [EXTRUDER_TEMP=<value>]
                        [BED_SOAK_MINUTES=<value>] [EXTRUDER_SOAK_MINUTES=<value>]
                        [DWELL_SECONDS=<value>] [DWELL_LIFT_Z=<value>]
                        [END_IDLE_MINUTES=<value>]

The temperatures are in Celsius.  The defaults are as follows:

    TEST_PROBE_ACCURACY START_IDLE_MINUTES=5
                        BED_TEMP=110 EXTRUDER_TEMP=240
                        BED_SOAK_MINUTES=30 EXTRUDER_SOAK_MINUTES=15
                        DWELL_SECONDS=1 DWELL_LIFT_Z=-1
                        END_IDLE_MINUTES=10

`START_IDLE_MINUTES` is the amount of time the test will wait at the start before heating up the bed.

Setting `BED_TEMP` or `EXTRUDER_TEMP` to `-1` allows you to disable heating and soaking the bed or
the extruder.  Thus you could run a test with just the extruder and without ever turning on the bed.

`DWELL_SECONDS` is the approximate amount of time between running `PROBE_ACCURACY` commands.  If
`DWELL_LIFT_Z` is not `-1`, then the toolhead will be lifted to the specified Z after completing
each `PROBE_ACCURACY`.  This is intended to allow the probe to cool away from the bed between probes.

`END_IDLE_MINUTES` is the amount of time the test will wait after turning off the heaters at the end,
while still measuring probe accuracy.



Mesh Bed Testing
======================
Thanks to @alch3my for inspiration and some code parts.

Installation
------------
As above include the `probe_accuracy/test_probe_accuracy.cfg` in your klipper configuration. Also [[bed_mesh]](https://github.com/KevinOConnor/klipper/blob/master/docs/Bed_Mesh.md#basic-configuration) has to be defined in the configuration.

Install the following dependencies.
To use the python environment approach issue
    
    sudo apt-get install libatlas-base-dev
    /home/pi/plotly-env/bin/pip install -U numpy matplotlib

Or use the system wide installation
    
    sudo apt install python3-numpy python3-matplotlib

For .gif creation you also need

    sudo apt install imagemagick

Test Execution
--------------
 
The same logic as above applies. Home and level your printer (G32 on a [VORON 2](https://vorondesign.com)).
Then start either

    /home/pi/plotly-env/bin/python3 bed_mesh.py

or with the system wide installation

    python3 bed_mesh.py

Then issue in klipper console (adjust to your liking):

    TEST_PROBE_ACCURACY START_IDLE_MINUTES=1 END_IDLE_MINUTES=1 BED_TEMP=105 EXTRUDER_TEMP=30 BED_SOAK_MINUTES=1 EXTRUDER_SOAK_MINUTES=1 BED_MESH=1

START_IDLE_MINUTES=0 and END_IDLE_MINUTES=0 does not work. Keep the session open during the test (see above for more). At the end .png files are created from the plots and placed in `/tmp/`.

For a .gif creation issue

    convert -delay 25 /tmp/mesh_*.png /tmp/meshes.gif

Currently you need to remove the old mesh images before you run another test:

    rm /tmp/mesh_*.png

Things to try out
--------------
 * Include a `G32` before each `BED_MESH_CALIBRATE` to relevel the gantry and reflect the actual state the printer will be in when printing after heat soak.
 * Remove the `relative_reference_index:` in [bed_mesh]. This might show the upwards tendency of the print head in the case of e.g. a Voron 2. See [Z-Axis Frame Thermal Expansion Compensation](https://github.com/alchemyEngine/klipper/tree/work-frame-expansion-20210130#z-axis-frame-thermal-expansion-compensation) for more. 