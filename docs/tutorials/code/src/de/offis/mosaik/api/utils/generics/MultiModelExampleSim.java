package de.offis.mosaik.api.utils.generics;

import java.util.Map;

/**
 * @author Alexander Hill
 */
public class MultiModelExampleSim extends MultiModelInputSimulator {
    private int stepSize = 60;

    public MultiModelExampleSim() {
        super("ExampleSim", SimulationType.TimeBased, AnnotatedExampleModel.class);

        registerStepMethod(MessageModel.class, this::parseInput);
        registerFinishCreationMethod(AnnotatedExampleModel.class, this::finishModelCreation);
    }

    private Map<String, AnnotatedExampleModel> finishModelCreation(Map<String, AnnotatedExampleModel> modelMap) {
        // Put you entity modifications or auxiliary calls here
        return modelMap;
    }

    @Override
    public void initialize(String sid, Float timeResolution, Map<String, Object> simParams) {
        if (simParams.containsKey("step_size")) {
            this.stepSize = ((Number) simParams.get("step_size")).intValue();
        }
    }

    private long parseInput(long time, Map<String, Map<String, InputMessage<MessageModel>>> inputResult, long maxAdvance) {
        inputResult.forEach((model, inputMessageMap) -> {
            getEntities(AnnotatedExampleModel.class)
                    .get(model)
                    .setDelta(inputMessageMap
                            .values()
                            .stream()
                            .mapToDouble(value -> value.getInputMessage().delta)
                            .sum());
        });
        return maxAdvance;
    }

    @Override
    public long simulationStep(long time, Map<String, Object> inputs, long maxAdvance) {
        getEntities(AnnotatedExampleModel.class).values().forEach(AnnotatedExampleModel::step);
        return time + stepSize;
    }
}
