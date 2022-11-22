package de.offis.mosaik.api.utils.generics;

import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

import de.offis.mosaik.api.SimProcess;
import de.offis.mosaik.api.Simulator;
import de.offis.mosaik.api.utils.generics.*;
import org.junit.Test;

public class ExampleModelSim extends ModelSimulator<AnnotatedExampleModel, AnnotatedExampleModel> {

    private int stepSize = 60;

    public ExampleModelSim() throws Exception {
        super("ExampleSim", SimulationType.TimeBased, AnnotatedExampleModel.class, AnnotatedExampleModel.class);
    }

    @Override
    public void initialize(String sid, Float timeResolution, Map<String, Object> simParams) {
        if (simParams.containsKey("step_size")) {
            this.stepSize = ((Number) simParams.get("step_size")).intValue();
        }
    }

    @Override
    public void finishEntityCreation(Map<String, AnnotatedExampleModel> entities) {
        // Change the entity map or call auxiliary methods here
    }

    @Override
    public void setupDone() throws Exception {
        // Call auxiliary methods after entities are created here
    }

    @Override
    public long modelStep(long time, Map<String, Collection<InputMessage<AnnotatedExampleModel>>> inputs, long maxAdvance) {
        for (String id :
                inputs.keySet()) {
            Collection<InputMessage<AnnotatedExampleModel>> modelCollection = inputs.get(id);
            double sum = modelCollection.stream().mapToDouble(modelInputMessage -> modelInputMessage.getInputMessage().getDelta()).sum();
            getEntities().get(id).setDelta(sum);
        }
        for (AnnotatedExampleModel instance : getEntities().values()) {
            instance.step();
        }

        return time + this.stepSize;
    }
}