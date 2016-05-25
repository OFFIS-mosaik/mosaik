package de.offis.mosaik.api.utils;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

/**
 * Facade for the {@code Map<String, Object>} parameter passed
 * by {@link de.offis.mosaik.api.Simulator#step(long, Map) step()}. 
 * Contains an array of 
 * {@link de.offis.mosaik.api.utils.InputForDestinationEntity 
 * InputForDestinationEntity}.
 * @author tLaue
 *
 */
public class StepInputs implements Iterable<InputForDestinationEntity>{
	
	private InputForDestinationEntity[] stepInputs;

	@SuppressWarnings("unused")
	private StepInputs() { }
	
	/**
	 * Instantiate a new StepInputs object.
	 * Throws an exception if inputs is null.
	 * @param inputs
	 */
	public StepInputs(Map<String, Object> inputs) {
		if (inputs == null) {
			throw new RuntimeException("inputs can't be null!");
		}
		Map<String, Map<String, Map<String, Object>>> inputs2 
		= convert(inputs);
		int i = 0;
		stepInputs = new InputForDestinationEntity[inputs2.size()];
		for (Map.Entry<String, Map<String, Map<String, Object>>> e : inputs2.entrySet()) {
			stepInputs[i] = new InputForDestinationEntity(e.getKey(), e.getValue());
			i++;
		}
	}

	/**
	 * Return the list of inputs for the destination entities.
	 * @return An array of inputs.
	 */
	public InputForDestinationEntity[] getInputList() {
		return stepInputs;
	}
	
	/**
	 * Find an input object by its destination entities ID.
	 * @param eid The ID of the destination entities inputs to be found.
	 * @return The input object, or null.
	 */
	public InputForDestinationEntity getInputByEID(String eid) {
		for(InputForDestinationEntity inputs: this.stepInputs) {
			if (inputs.getDestinatonEid().equals(eid)) {
				return inputs;
			}
		}
		return null;
	}

	@Override
	public Iterator<InputForDestinationEntity> iterator() {
		return Arrays.asList(stepInputs).iterator();
	}
	
	@SuppressWarnings("unchecked")
	private Map<String, Map<String, Map<String, Object>>> convert(Map<String, Object> inputs) {
		Map<String, Map<String, Map<String, Object>>> result = new HashMap<String, Map<String, Map<String, Object>>>();
		for (Map.Entry<String, Object> entity : inputs.entrySet()) {
            Map<String, Map<String, Object>> attrs = (Map<String, Map<String, Object>>) entity.getValue();
            result.put(entity.getKey(), attrs);
		}
		return result;
	}
}
