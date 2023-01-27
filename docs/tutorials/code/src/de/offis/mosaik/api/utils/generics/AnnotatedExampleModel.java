package de.offis.mosaik.api.utils.generics;

/**
 * @author Alexander Hill
 */
@Model("ExampleModel")
public class AnnotatedExampleModel {
    private Double val;
    private Double delta = 1.d;

    public AnnotatedExampleModel() {
        this.val = 0.d;
    }

    @Model.Constructor
    public AnnotatedExampleModel(@Model.Param("init_val") Double initVal) {
        this.val = initVal;
    }

    public Double getVal() {
        return this.val;
    }

    public Double getDelta() {
        return this.delta;
    }

    public void setDelta(Double delta) {
        this.delta = delta;
    }

    public void step() {
        this.val += this.delta;
    }
}
