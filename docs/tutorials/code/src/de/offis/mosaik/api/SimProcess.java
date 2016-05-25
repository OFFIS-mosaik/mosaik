package de.offis.mosaik.api;

import java.util.logging.Level;
import java.util.logging.LogManager;
import java.util.logging.Logger;

import org.json.simple.JSONObject;

import de.offis.mosaik.api.SimpyIoSocket.Request;

/**
 * This class provides the network event loop and method dispatcher for your
 * simulation.
 */
public class SimProcess {
    /**
     * This method should be called from your <code>main()</code> in order
     * to start the simulation.
     *
     * @param args is list list of command line arguments.
     * @param sim is the instance of your simulator class.
     * @throws Exception
     */
    public static void startSimulation(String[] args, Simulator sim)
            throws Exception {
        final String addr = args[0]; // e.g., "localhost:5555"

        // TODO: Read level from *args* and use LogManager to configure logging
        // logging for all loggers. Use https://github.com/docopt/docopt.java
        LogManager.getLogManager().addLogger(SimProcess.logger);
        SimProcess.logger.setLevel(Level.FINE);

        sim.configure(args);

        try {
            SimProcess.logger.info("Starting " + sim.getSimName() + " ...");
            final SimProcess server = new SimProcess(addr, sim);
            server.run();
        } catch (final Exception e) {
            e.printStackTrace();
            throw e;
        } finally {
            sim.cleanup();
        }
    }

    public static Logger logger = Logger.getLogger(SimProcess.class.getName());

    private final SimpyIoSocket sock;
    private final Simulator sim;
    private boolean stop;

    /**
     * @param addr is mosaik's network address <em>host:port</em>.
     * @param simulator is the simulator instance.
     * @throws Exception
     */
    private SimProcess(String addr, Simulator simulator) throws Exception {
        this.sock = new SimpyIoSocket(addr);
        this.sim = simulator;
        this.stop = false;

        this.sim.setMosaik(new MosaikProxy(this.sock));
    }

    /**
     * This method implements the event-loop.
     *
     * It dispatches method call requests until it receives a <em>stop</em>
     * message.
     *
     * @throws Exception
     */
    @SuppressWarnings("unchecked")
    public void run() throws Exception {
        Request req;
        Object result;

        eventloop: while (!this.stop) {
            req = this.sock.recvRequest();

            switch (req.method) {
            case "init":
                final String sid = (String) req.args.get(0);
                result = this.sim.init(sid, req.kwargs);
                break;

            case "create":
                final int num = ((Number) req.args.get(0)).intValue();
                final String model = (String) req.args.get(1);
                result = this.sim.create(num, model, req.kwargs);
                break;

            case "setup_done":
                result = null;
                this.sim.setupDone();
                break;

            case "step":
                final long time = ((Number) req.args.get(0)).longValue();
                final JSONObject inputs = (JSONObject) req.args.get(1);
                result = this.sim.step(time, inputs);
                break;

            case "get_data":
                final JSONObject outputs = (JSONObject) req.args.get(0);
                result = this.sim.getData(outputs);
                break;

            case "stop":
                this.stop = true;
                break eventloop;

            default:
                throw new RuntimeException("Unkown method: " + req.method);
            }
            req.reply(result);
        }
        this.sock.close();
        SimProcess.logger.info(sim.getSimName() + " finished");
    }
}
