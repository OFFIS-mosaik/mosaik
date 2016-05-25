package de.offis.mosaik.api;

import java.util.List;
import java.util.Map;

/**
 * This class should be implemented by a concrete simulation. An instance of
 * it will be used by {@link SimProcess#startSimulation(String[], Simulation)
 * SimProcess.startSimulation}.
 *
 * The methods of this class will receive and should return of a lot of lists
 * and maps. These are the direct outputs of json-simple's {@link
 * org.json.simple.parser.JSONParser#parse(String) parse} method or serve as
 * input for the JSON encoding. The <a href=
 * "http://code.google.com/p/json-simple/wiki/MappingBetweenJSONAndJavaEntities"
 * >project wiki</a> contains a list with mappings between JSON and Java types.
 *
 * The <a href="https://mosaik.readthedocs.org/en/latest/mosaik-api/">mosaik
 * documentation</a> contains a detailed description of the low-level JSON API
 * which can be used to see what a <code>List<Object></code> or
 * <code>Map<String, Object></code> contains or should contain.
 */
public abstract class Simulator {
    public static final String API_VERSION = "2.2";
    private final String simName;
    private MosaikProxy mosaik;

    /**
     * Create a new simulator instance.
     *
     * @param simName is the simulation's name.
     */
    public Simulator(String simName) {
        this.simName = simName;
    }

    /**
     * Get the name of this simulation.
     *
     * @return the name of this simulation.
     */
    public String getSimName() {
        return this.simName;
    }

    /**
     * Get the mosaik proxy.
     *
     * @return the mosaik proxy instance.
     */
    public MosaikProxy getMosaik() {
        return this.mosaik;
    }

    /**
     * Set the mosaik proxy.
     *
     * @param mosaik is the mosaik proxy instance.
     */
    protected void setMosaik(MosaikProxy mosaik) {
        this.mosaik = mosaik;
    }

    /**
     * Initialize the simulator with the ID <em>sid</em> and apply additional
     * parameters <em>(simParams)</em> sent by mosaik.
     *
     * @param sid is the ID mosaik has given to this simulator.
     * @param simParams a map with additional simulation parameters.
     * @return the meta data dictionary (see {@link
     *         https://mosaik.readthedocs.org/en/latest/mosaik-api/low-level.html#init}).
     * @throws Exception
     */
    public abstract Map<String, Object> init(String sid, Map<String, Object>
            simParams) throws Exception;

    /**
     * Create <em>num</em> instances of <em>model</em> using the provided
     * <em>model_params</em>.
     *
     * @param num is the number of instances to create.
     * @param model is the name of the model to instantiate. It needs to be
     *              listed in the simulator's meta data and be public.
     * @param modelParams is a map containing additional model parameters.
     * @return a (nested) list of maps describing the created entities (model
     *         instances) (see {@link
     *         https://mosaik.readthedocs.org/en/latest/mosaik-api/low-level.html#create}).
     * @throws Exception
     */
    public abstract List<Map<String, Object>> create(int num, String model,
            Map<String, Object> modelParams) throws Exception;
    
    /**
     * Callback that indicates that the scenario setup is done and the 
     * actual simulation is about to start. At this point, all entities 
     * and all connections between them are know but no simulator has 
     * been stepped yet. Implementing this method is optional.
     * Added in mosaik API version 3.
     * 
     * @throws Exception
     */
    public void setupDone() throws Exception {
    	
	}

    /**
     * Perform the next simulation step from time <em>time</em> using input
     * values from <em>inputs</em> and return the new simulation time (the time
     * at which <code>step()</code> should be called again).
     *
     * @param time is the current time in seconds from simulation start.
     * @param inputs is a map of input values (see {@link
     *               https://mosaik.readthedocs.org/en/latest/mosaik-api/low-level.html#step}).
     * @return the time at which this method should be called again in seconds
     *         since simulation start.
     * @throws Exception
     */
    public abstract long step(long time, Map<String, Object> inputs)
            throws Exception;

    /**
     * Return the data for the requested attributes in *outputs*
     *
     * @param outputs is a mapping of entity IDs to lists of attribute names.
     * @return a mapping of the same entity IDs to maps with attributes and
     *         their values (see {@link
     *         https://mosaik.readthedocs.org/en/latest/mosaik-api/low-level.html#get-data}).
     * @throws Exception
     */
    public abstract Map<String, Object> getData(
            Map<String, List<String>> outputs) throws Exception;

    /**
     * This method can be overridden to configure the simulation with the
     * command line *args*.
     *
     * The default implementation simply ignores them.
     *
     * @param args is a list of command line arguments.
     * @throws Exception
     */
    public void configure(String[] args) throws Exception {
    	if (args.length > 1) {
    		if (args[1].toLowerCase().equals("server")) {
    			SimpyIoSocket.isServer = true;	
    		}
    	}
        return;
    }

    /**
     * This method is executed just before the sim process stops.
     *
     * Use this to perform some clean-up, e.g., to terminate external processes
     * that you started or to join threads.
     *
     * @throws Exception
     */
    public void cleanup() throws Exception {
        return;
    }
}
