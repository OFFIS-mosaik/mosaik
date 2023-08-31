package de.offis.mosaik.api.utils.generics;

import de.offis.mosaik.api.SimProcess;
import de.offis.mosaik.api.Simulator;

/**
 * @author Alexander Hill
 */
public class SimulationStarter {
    public static void main(String[] args) throws Throwable {
        Simulator sim = new ExampleModelSim();
        //TODO: Implement command line arguments parser (http://commons.apache.org/proper/commons-cli/)
        if (args.length < 1) {
            String ipaddr[] = {"127.0.0.1:5678"};
            SimProcess.startSimulation(ipaddr, sim);
        } else {
            SimProcess.startSimulation(args, sim);
        }
    }
}
