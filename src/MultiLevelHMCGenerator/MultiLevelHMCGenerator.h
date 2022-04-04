/**
 * @file       MultiLevelHMCGenerator.h
 * @brief      Declarations of Multi level HMC
 * @author     nico
 * @version    0.0.1
 * @date       26.03.22
 */


#ifndef BACHELOR_THESIS_MULTILEVELHMCGENERATOR_H
#define BACHELOR_THESIS_MULTILEVELHMCGENERATOR_H

#include <BaseModel.h>
#include <HMCGenerator.h>
#include <random>
#include <iostream>

#include <utility>
#include <memory>

/**
 * @brief Template of the Multilevel HMC algorithm
 * @tparam configuration_type Datatype, which is used for the configurations of the model
 */
template<class configuration_type>
class MultiLevelHMCGenerator {
public:
    /**
     * @brief Constructor of the Multi Level HMC generator
     * @param model_ Model for which to generate ensembles
     * @param nu_pre_ Amount of pre coarsening steps to take at each level
     * @param nu_post_ Amount of post coarsening steps to take at each level
     * @param gamma_ Amount of repetitions at each level (determines if a 'V' or 'W' or ... cycle is performed)
     * @param InterpolationType_ Interpolation type used to generate the coarser levels
     * @param amount_of_steps_ Amount of steps to be used in the integration process for each level
     * @param step_sizes_ Step size in the integration process for each level
     * @param generator_ Random number generator to be used for the HMC process
     */
    MultiLevelHMCGenerator(BaseModel<configuration_type> &model_, std::vector<size_t> nu_pre_,
                           std::vector<size_t> nu_post_, size_t gamma_,
                           InterpolationType InterpolationType_,
                           const std::vector<size_t> &amount_of_steps_, const std::vector<double> &step_sizes_,
                           std::default_random_engine &generator_);

    /**
     * @brief Generate \p amount_of_samples amount of ensembles, starting from \p phiStart and doing
     *        \p amount_of_thermalization_steps thermalization steps in advance
     * @param phiStart Starting field
     * @param amount_of_samples Amount of samples to take
     * @param amount_of_thermalization_steps Amount of thermalization steps
     * @return Acceptance rates
     */
    std::vector<double> generate_ensembles(const configuration_type &phiStart,
                                           size_t amount_of_samples, size_t amount_of_thermalization_steps = 10);

    /**
     * @brief Compute the \p observable_function_pointer of the currently loaded ensemble
     * @return vector of observable
     */
    void dump_observable(double (
    BaseModel<configuration_type>::*observable_function_pointer)(const configuration_type &),
                         const std::string &name, HighFive::File &file);

    void dumpToH5(HighFive::File &file);

    void propagate_update();


private:
    /**
     * @brief Recursion to go to coarser levels
     * @param level Current level id (finest=0, coarsest=\c nu_pre.size()-1 )
     * @param phi Starting configuration/field
     * @return Updated configuration/field
     */
    configuration_type LevelRecursion(int level, const configuration_type &phi);

    /**
     * @brief Amount of pre coarsening steps to take at each level
     */
    std::vector<size_t> nu_pre;

    /**
     * @brief Amount of post coarsening steps to take at each level
     */
    std::vector<size_t> nu_post;

    /**
     * @brief Amount of repetitions at each level (determines if a 'V' or 'W' or ... cycle is performed)
     */
    size_t gamma;

    /**
     * @brief Interpolation type used to generate the coarser levels
     */
    InterpolationType inter_type;

    /**
     * @brief Random number generator to be used for the HMC process
     */
    std::default_random_engine &generator;

    /**
     * @brief Stores the HMC generator for each level
     */
    std::vector<HMCGenerator<configuration_type>> HMCStack;

    /**
     * @brief Stores the model for each level
     */
    std::vector<std::unique_ptr<BaseModel<configuration_type>>> ModelStack;

    /**
     * @brief Saves the Acceptance rate at each level
     */
    std::vector<double> AcceptanceRates;
};

template<class configuration_type>
MultiLevelHMCGenerator<configuration_type>::MultiLevelHMCGenerator(BaseModel<configuration_type> &model_,
                                                                   std::vector<size_t> nu_pre_,
                                                                   std::vector<size_t> nu_post_,
                                                                   size_t gamma_,
                                                                   InterpolationType InterpolationType_,
                                                                   const std::vector<size_t> &amount_of_steps_,
                                                                   const std::vector<double> &step_sizes_,
                                                                   std::default_random_engine &generator_)
        : nu_pre{std::move(nu_pre_)}, nu_post{std::move(nu_post_)}, gamma{gamma_}, inter_type{InterpolationType_},
          generator{generator_}, AcceptanceRates{} {
    //TODO: add auto sizing
    assert(gamma > 0);
    assert(nu_pre.size() == nu_post.size());
    assert(nu_pre.size() == amount_of_steps_.size());
    assert(nu_pre.size() == step_sizes_.size());


    AcceptanceRates.resize(nu_pre.size());
    ModelStack.push_back(std::unique_ptr<BaseModel<configuration_type>>(model_.get_copy_of_model()));
    HMCStack.push_back(HMCGenerator(model_, amount_of_steps_[0], step_sizes_[0], generator));

    for (int i = 1; i < nu_pre.size(); ++i) {
        assert(nu_pre[i] + nu_post[i] > 0);
        ModelStack.push_back(
                std::unique_ptr<BaseModel<configuration_type>>(
                        (ModelStack[i - 1])->get_coarser_model(inter_type)));
        HMCStack.push_back(HMCGenerator(*ModelStack[i], amount_of_steps_[i], step_sizes_[i], generator));
    }

}

template<class configuration_type>
std::vector<double> MultiLevelHMCGenerator<configuration_type>::generate_ensembles(const configuration_type &phiStart,
                                                                                   size_t amount_of_samples,
                                                                                   size_t amount_of_thermalization_steps) {
    configuration_type phi(phiStart);
    for (int i = 0; i < amount_of_thermalization_steps; ++i) {
        phi = LevelRecursion(0, phi);
    }
    HMCStack[0].clear_ensembles();
    for (auto &elem: AcceptanceRates) {
        elem = 0.;
    }
    for (int i = 0; i < amount_of_samples; ++i) {
        phi = LevelRecursion(0, phi);
    }

    for (int i = 0; i < AcceptanceRates.size(); ++i) {
        AcceptanceRates[i] = AcceptanceRates[i] / (amount_of_samples * (nu_pre[i] + nu_post[i]) * int_pow(gamma, i));
    }
    return AcceptanceRates;
}

template<class configuration_type>
configuration_type
MultiLevelHMCGenerator<configuration_type>::LevelRecursion(int level, const configuration_type &phi) {
    configuration_type currentField{phi};
    AcceptanceRates[level] += HMCStack[level].generate_ensembles(currentField, nu_pre[level], 0, level == 0);
    currentField = HMCStack[level].get_last_configuration(currentField);
    //std::cout << "Level:\t" << level << std::endl;

    if (level < (nu_pre.size() - 1)) {
        ModelStack[level + 1]->update_fields(currentField);
        configuration_type CoarseCorrections = ModelStack[level + 1]->get_empty_field();
        for (int i = 0; i < gamma; ++i) {
            CoarseCorrections = LevelRecursion(level + 1, CoarseCorrections);
        }
        ModelStack[level + 1]->interpolate(CoarseCorrections, currentField);
    }
    AcceptanceRates[level] += HMCStack[level].generate_ensembles(currentField, nu_post[level], 0, level == 0);
    return HMCStack[level].get_last_configuration(currentField);
}

template<class configuration_type>
void MultiLevelHMCGenerator<configuration_type>::propagate_update() {
    for (int i = 1; i < ModelStack.size(); ++i) {
        ModelStack[i]->pull_attributes_from_finer_level();
    }
}


template<class configuration_type>
void MultiLevelHMCGenerator<configuration_type>::dumpToH5(HighFive::File &file) {
    //TODO
    HighFive::Group level0 = file.getGroup(file.getPath());
    if (file.exist("level0")) {
        level0 = file.getGroup("level0");
    } else {
        level0 = file.createGroup("level0");
    }
    HMCStack[0].dumpToH5(level0);
}

template<class configuration_type>
void MultiLevelHMCGenerator<configuration_type>::dump_observable(
        double (BaseModel<configuration_type>::*observable_function_pointer)(const configuration_type &),
        const std::string &name, HighFive::File &file) {

    HighFive::Group level0 = file.getGroup(file.getPath());
    if (file.exist("level0")) {
        level0 = file.getGroup("level0");
    } else {
        level0 = file.createGroup("level0");
    }
    HMCStack[0].dump_observable(observable_function_pointer, name, level0);
}


#endif //BACHELOR_THESIS_MULTILEVELHMCGENERATOR_H
